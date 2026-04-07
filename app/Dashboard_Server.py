import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import time
import os
from collections import deque

# --- KONFIGURATION ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "mbm/projekt/daten/all"
DATA_FILE = "data/vorlesung_daten.csv"

st.set_page_config(page_title="Dozenten Dashboard", layout="wide")

# --- GLOBALER ZWISCHENSPEICHER (Der Briefkasten) ---
if 'INCOMING_QUEUE' not in globals():
    global INCOMING_QUEUE
    INCOMING_QUEUE = {}

# --- SPEICHER INITIALISIEREN ---
if 'class_data' not in st.session_state:
    st.session_state.class_data = {} 

if 'history' not in st.session_state:
    st.session_state.history = deque(maxlen=100)
    
if 'recorded_data' not in st.session_state:
    st.session_state.recorded_data = []

if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()

# --- MQTT EMPFÄNGER FUNKTION ---
def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        s_id = data['id']
        s_status = data['status'].upper() 
        INCOMING_QUEUE[s_id] = s_status
    except Exception as e:
        pass 

# --- MQTT STARTEN ---
@st.cache_resource
def start_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, 60)
        client.subscribe(TOPIC)
        client.loop_start()
    except:
        pass
    return client

mqtt_client = start_mqtt()

# --- MODUS WÄHLEN ---
st.sidebar.title("🎛️ Steuerung")
mode = st.sidebar.radio("Ansicht:", ["🔴 Live-Vorlesung", "🎬 Nachbereitung (Analyse)"])

# ==========================================
# MODUS 1: LIVE VORLESUNG
# ==========================================
if mode == "🔴 Live-Vorlesung":
    st.title("🏫 Live Classroom Analytics")

    dashboard_placeholder = st.empty()

    st.sidebar.markdown("---")
    stop = st.sidebar.checkbox("Dashboard läuft", value=True)
    
    if st.sidebar.button("Reset / Neue Vorlesung"):
        st.session_state.class_data = {}
        st.session_state.history.clear()
        st.session_state.recorded_data = []
        st.session_state.start_time = time.time()
        INCOMING_QUEUE.clear()
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)

    icons = {"KONZENTRATION": "🟣", "NEUTRAL": "🔵", "ABGELENKT": "⚪"}

    # --- HAUPTSCHLEIFE ---
    while stop:
        
        # 1. DATEN ÜBERTRAGEN
        if len(INCOMING_QUEUE) > 0:
            st.session_state.class_data.update(INCOMING_QUEUE)
        
        # 2. Aktuelle Daten holen
        active_students = st.session_state.class_data
        total = len(active_students)
        
        # 3. Statistik berechnen
        if total > 0:
            counts = list(active_students.values())
            konz = counts.count("KONZENTRATION")
            neut = counts.count("NEUTRAL")
            abge = counts.count("ABGELENKT")
            score_sum = (konz * 100) + (neut * 50) + (abge * 0)
            avg_score = score_sum / total
        else:
            konz = neut = abge = 0
            avg_score = 0
        
        st.session_state.history.append(avg_score)

        # 4. DATEN FÜR NACHBEREITUNG SPEICHERN
        elapsed = round(time.time() - st.session_state.start_time, 1)
        st.session_state.recorded_data.append([elapsed, avg_score])
        
        # Die CSV wird bei jedem Durchlauf neu gespeichert
        os.makedirs("data", exist_ok=True)  # Erstellt den Ordner, falls er fehlt
        df_save = pd.DataFrame(st.session_state.recorded_data, columns=["Sekunde", "Fokus"])
        df_save.to_csv(DATA_FILE, index=False)
        
        # 5. Zeichnen
        with dashboard_placeholder.container():
            k1, k2, k3 = st.columns(3)
            perc_konz = int(konz/total*100) if total > 0 else 0
            k1.metric("🟣 Konzentration", f"{konz}", f"{perc_konz}%")
            k2.metric("🔵 Neutral", f"{neut}")
            k3.metric("⚪ Abgelenkt", f"{abge}")
            
            st.markdown("---")
            st.subheader(f"Aktive Studenten: {total}")
            
            if total == 0:
                st.info("📡 Warte auf Daten... (Programm läuft)")

            cols = st.columns(4)
            for i, (name, status) in enumerate(active_students.items()):
                col_idx = i % 4
                with cols[col_idx]:
                    border_color = "#444"
                    if status == "KONZENTRATION": border_color = "#9bf6ff"
                    if status == "ABGELENKT": border_color = "#ff4b4b"

                    st.markdown(f"""
                    <div style="border: 3px solid {border_color}; padding: 15px; border-radius: 10px; text-align: center; background-color: #262730; margin-bottom: 10px;">
                        <div style="font-size: 40px;">{icons.get(status, '❓')}</div>
                        <h3 style="margin:0; padding:0; color: white;">{name}</h3>
                        <p style="margin:0; color: #aaa;">{status}</p>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown("---")
            st.subheader("Klassen-Trend (Live)")
            chart_data = pd.DataFrame(list(st.session_state.history), columns=["Fokus"])
            st.line_chart(chart_data)

        time.sleep(0.5)

# ==========================================
# MODUS 2: NACHBEREITUNG & ANALYSE
# ==========================================
elif mode == "🎬 Nachbereitung (Analyse)":
    st.title("🎬 Vorlesungs-Analyse (Nachbereitung)")
    
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        
        if len(df) > 0:
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔧 Filter-Einstellungen")
            use_filter = st.sidebar.checkbox("📉 Gaußschen Weichzeichner anwenden", value=True)
            filter_strength = st.sidebar.slider("Glättungs-Stärke", 1, 50, 10)
            
            # Filter anwenden
            if use_filter:
                df["Anzeige_Fokus"] = df["Fokus"].rolling(window=filter_strength, min_periods=1, center=True).mean()
            else:
                df["Anzeige_Fokus"] = df["Fokus"]

            # --- STATISTIKEN ---
            st.markdown("### 📊 Zusammenfassung der Sitzung")
            col1, col2, col3 = st.columns(3)
            
            dauer_minuten = round(df["Sekunde"].max() / 60, 1)
            durchschnitt = int(df["Fokus"].mean())
            tiefpunkt = int(df["Fokus"].min())
            
            col1.metric("⏱️ Dauer der Aufzeichnung", f"{dauer_minuten} Min.")
            col2.metric("📈 Durchschnittlicher Fokus", f"{durchschnitt}%")
            col3.metric("📉 Niedrigster Fokus-Wert", f"{tiefpunkt}%")
            
            st.markdown("---")
            
            # --- GRAPH ---
            st.subheader("Visualisierung des Konzentrations-Verlaufs")
            st.line_chart(df.set_index("Sekunde")["Anzeige_Fokus"])
            
            if use_filter:
                st.info("💡 **Hinweis zum Weichzeichner:** Die Kurve wurde geglättet. Einzelne Messfehler der KI werden ignoriert, um den wahren Aufmerksamkeits-Trend der Klasse sichtbar zu machen.")
            else:
                st.warning("⚠️ **Rohdaten-Ansicht:** Die Kurve zeigt die ungefilterten Messwerte. Starke Ausschläge (Rauschen) sind normales Verhalten der KI-Sensorik.")
                
        else:
            st.warning("Die Datei ist leer. Es wurden noch keine Daten gesammelt.")
            
    else:
        st.warning("Es wurden noch keine Daten aufgezeichnet. Bitte starte zuerst eine Live-Vorlesung.")