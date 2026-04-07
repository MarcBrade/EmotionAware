import streamlit as st
import cv2
import mediapipe as mp
import math
import numpy as np          # WICHTIG: Für die Mathe-Berechnungen
from deepface import DeepFace
import paho.mqtt.client as mqtt
import json
import time
import os

# --- SYSTEM-FIX ---
# Verhindert Fehler bei neueren TensorFlow-Versionen
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import tensorflow as tf
import tf_keras
if not hasattr(tf, 'keras'): tf.keras = tf_keras

# --- KONFIGURATION ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_BASE = "mbm/projekt/daten/" 
BROW_THRESHOLD = 0.20

st.set_page_config(page_title="Student Sender", layout="centered")

# --- UI ---
st.title("👨‍🎓 Student App")
st.info("Diese App analysiert dein Gesicht lokal. Wähle die Kamera-Quelle 1, falls du Zoom parallel nutzt (via OBS).")

# Kamera-Auswahl für Zoom-Kompatibilität
cam_index = st.selectbox("Kamera-Quelle wählen:", 
                         options=[0, 1, 2, 3], 
                         format_func=lambda x: f"Kamera {x} (Standard=0, OBS/Virtuell oft 1)")

student_id = st.text_input("Dein Name:", value="Student 1")
run_analysis = st.toggle("Senden Starten", value=False)

# --- HELPER FUNKTIONEN ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(min_detection_confidence=0.5, min_tracking_confidence=0.5)

def get_head_pose(image, face_landmarks):
    # Sicherstellen, dass numpy da ist
    import numpy as np
    
    img_h, img_w, img_c = image.shape
    face_3d = []
    face_2d = []
    landmark_ids = [33, 263, 1, 61, 291, 199]
    for idx, lm in enumerate(face_landmarks.landmark):
        if idx in landmark_ids:
            if idx == 1:
                nose_2d = (lm.x * img_w, lm.y * img_h)
                nose_3d = (lm.x * img_w, lm.y * img_h, lm.z * 3000)
            x, y = int(lm.x * img_w), int(lm.y * img_h)
            face_2d.append([x, y])
            face_3d.append([x, y, lm.z])       
    
    face_2d = np.array(face_2d, dtype=np.float64)
    face_3d = np.array(face_3d, dtype=np.float64)
    focal_length = 1 * img_w
    cam_matrix = np.array([[focal_length, 0, img_h / 2], [0, focal_length, img_w / 2], [0, 0, 1]])
    dist_matrix = np.zeros((4, 1), dtype=np.float64)
    success, rot_vec, trans_vec = cv2.solvePnP(face_3d, face_2d, cam_matrix, dist_matrix)
    rmat, jac = cv2.Rodrigues(rot_vec)
    angles, mtxR, mtxQ, Qx, mtxQ, Qz = cv2.RQDecomp3x3(rmat)
    x = angles[0] * 360
    y = angles[1] * 360
    if y < -10: return "LEFT"
    if y > 10: return "RIGHT"
    if x < -10: return "DOWN"
    if x > 10: return "UP"
    return "CENTER"

def get_brow_tension(face_landmarks):
    brow_left = face_landmarks.landmark[107]
    brow_right = face_landmarks.landmark[336]
    ear_left = face_landmarks.landmark[234]
    ear_right = face_landmarks.landmark[454]
    brow_dist = math.sqrt((brow_left.x - brow_right.x)**2 + (brow_left.y - brow_right.y)**2)
    face_width = math.sqrt((ear_left.x - ear_right.x)**2 + (ear_left.y - ear_right.y)**2)
    return brow_dist / face_width

def get_simple_state(emotions_dict: dict, head_pose: str, brow_ratio: float) -> str:
    if head_pose in ["LEFT", "RIGHT", "UP"]: return "ABGELENKT"
    if head_pose == "DOWN": return "KONZENTRATION" # Blick ins Buch/Heft
    if brow_ratio < BROW_THRESHOLD: return "KONZENTRATION" # Stirnrunzeln
    
    # Emotionen prüfen
    score_intensity = (emotions_dict.get('sad', 0) + emotions_dict.get('fear', 0) + 
                       emotions_dict.get('disgust', 0) + emotions_dict.get('angry', 0))
    if score_intensity > 30.0: return "KONZENTRATION" # "Angestrengt"
    
    return "NEUTRAL"

# --- MQTT SETUP ---
client = mqtt.Client()
try:
    client.connect(BROKER, PORT, 60)
except:
    st.warning("⚠️ MQTT Offline - Prüfe Internet/Firewall (Hotspot nutzen!)")

# --- HAUPTSCHLEIFE ---
if run_analysis:
    # Hier nutzen wir die ausgewählte Kamera-Nummer
    if os.name == 'nt':
        cam = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
    else:
        cam = cv2.VideoCapture(cam_index)
    
    # Prüfen, ob Kamera wirklich geht
    if not cam.isOpened():
        st.error(f"❌ Fehler: Kamera {cam_index} konnte nicht geöffnet werden. Probiere eine andere Nummer im Menü oben!")
        st.stop()

    video_placeholder = st.empty()
    status_text = st.empty()
    frame_count = 0
    current_emotions = {'neutral': 100}

    while run_analysis:
        ret, frame = cam.read()
        if not ret:
            st.warning("Kamera-Signal verloren.")
            break
        
        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        state = "NEUTRAL"
        
        results_mesh = face_mesh.process(frame_rgb)
        if results_mesh.multi_face_landmarks:
            for face_landmarks in results_mesh.multi_face_landmarks:
                pose = get_head_pose(frame, face_landmarks)
                brow = get_brow_tension(face_landmarks)
                
                # Visualisierung: Blaue Linie auf Stirn bei Konzentration
                if brow < BROW_THRESHOLD:
                     p1 = face_landmarks.landmark[107]; p2 = face_landmarks.landmark[336]
                     h, w, c = frame.shape
                     cv2.line(frame_rgb, (int(p1.x*w), int(p1.y*h)), (int(p2.x*w), int(p2.y*h)), (255, 0, 0), 3)

                # Emotion (DeepFace nur alle 10 Frames für Performance)
                if frame_count % 10 == 0:
                    try:
                        res = DeepFace.analyze(frame, actions=['emotion'], enforce_detection=False)
                        if res: current_emotions = res[0]['emotion']
                    except: pass
                
                state = get_simple_state(current_emotions, pose, brow)

        # --- SENDEN ---
        if frame_count % 5 == 0: 
            try:
                payload = json.dumps({"id": student_id, "status": state})
                client.publish(TOPIC_BASE + "all", payload)
            except: pass

        # Lokale Anzeige
        cv2.putText(frame_rgb, f"Status: {state}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Zeige Bild im Browser
        video_placeholder.image(frame_rgb, channels="RGB", use_column_width=True)
        status_text.markdown(f"Status: **{state}** | ID: **{student_id}** | Kamera: **{cam_index}**")
        
        frame_count += 1
        time.sleep(0.01)

    cam.release()