# EmotionAware 🎓

EmotionAware ist eine datenschutzkonforme Edge-AI-Architektur zur Analyse und Reflexion von Aufmerksamkeitszuständen in der synchronen Online-Lehre. Das Projekt ermöglicht es Lehrkräften, während einer Online-Vorlesung ein anonymisiertes Echtzeit-Feedback zur Konzentration der Klasse zu erhalten. Gleichzeitig bietet es eine fundierte Basis für die datenbasierte didaktische Selbstreflexion nach der Lehrveranstaltung.

## ✨ Hauptfunktionen

* **Privacy by Design:** Die gesamte KI-Bildanalyse (Mimik und Kopfhaltung) findet ausschließlich lokal auf den Endgeräten der Studierenden statt. Es werden keine Videobilder übertragen.
* **Ressourcenschonende Kommunikation:** Die Übertragung der aggregierten Zustände erfolgt über das leichtgewichtige MQTT-Protokoll.
* **Live-Dashboard:** Eine interaktive Streamlit-Webanwendung visualisiert den globalen Fokus der Klasse in Echtzeit.
* **Nachbereitungs-Modus:** Automatische Protokollierung der Konzentrationsdaten inklusive eines gleitenden Durchschnittsfilters (Gaußscher Weichzeichner) zur Analyse des pädagogischen Trends.

## 📂 Projektstruktur

* `app/` enthält den ausführbaren Python-Code (Dozenten-Dashboard und Studenten-Client).
* `data/` dient als lokaler Speicherort für die automatisch generierten CSV-Dateien.
* `docs/` beinhaltet die schriftliche Ausarbeitung und Dokumentation des Projekts.
* `requirements.txt` listet alle benötigten Python-Bibliotheken auf.

## ⚙️ Systemvoraussetzungen

* Python 3.9 oder neuer installiert.
* Eine funktionierende Webcam (physisch oder virtuell via OBS Studio).
* Eine aktive Internetverbindung für den MQTT-Broker.

## 🚀 Installation und Setup

Befolgen Sie diese Schritte, um das Projekt auf Ihrem lokalen Rechner auszuführen. Öffnen Sie dazu Ihr Terminal (PowerShell oder Command Prompt) im Hauptordner des Projekts.

**1. Virtuelle Umgebung erstellen**
Es wird dringend empfohlen, eine virtuelle Umgebung zu nutzen, um Konflikte mit anderen Projekten zu vermeiden:
`python -m venv venv`

**2. Virtuelle Umgebung aktivieren**
* Auf Windows:
  `.\venv\Scripts\activate`
* Auf macOS / Linux:
  `source venv/bin/activate`

**3. Abhängigkeiten installieren**
Laden Sie alle benötigten Bibliotheken (wie Streamlit, OpenCV, MediaPipe und DeepFace) herunter:
`pip install -r requirements.txt`

## 🖥️ Ausführung

Das System besteht aus zwei Komponenten, die idealerweise parallel getestet werden.

**Schritt 1: Das Dozenten-Dashboard starten**
Starten Sie das Dashboard in Ihrem aktivierten Terminal mit folgendem Befehl:
`streamlit run app/dozent_dashboard.py`

Ihr Standard-Webbrowser öffnet sich nun automatisch mit der Benutzeroberfläche.

**Schritt 2: Kamera-Setup prüfen (Wichtig für OBS!)**
Falls Sie eine virtuelle Kamera nutzen (z.B. um parallel in Zoom sichtbar zu sein), öffnen Sie jetzt **OBS Studio** und klicken Sie auf **"Virtuelle Kamera starten"**.

**Schritt 3: Den Studenten-Client simulieren**
Öffnen Sie ein zweites Terminalfenster, aktivieren Sie auch dort die virtuelle Umgebung und starten Sie den Sensor-Client:
`python app/student_client.py`

*Wichtiger Hinweis zur Kamera-Auswahl:* Achten Sie darauf, als Student **Kamera 1** auszuwählen. Da die interne Laptop-Kamera meistens den Standardplatz (Kamera 0) belegt, wird die virtuelle OBS-Kamera vom System in der Regel als Kamera 1 erkannt. Sobald die richtige Kamera aktiv ist, sendet der Client die analysierten Daten an das Dashboard.

## 🛑 Wichtige Hinweise zur Bedienung

* **Beenden der Aufzeichnung:** Um eine laufende Live-Vorlesung korrekt zu speichern, entfernen Sie im Dashboard den Haken bei "Dashboard läuft". Warten Sie auf die grüne Erfolgsmeldung, bevor Sie das Terminal schließen. Nur so wird die CSV-Datei sicher abgeschlossen.
* **Abbruch im Terminal:** Programme im Terminal beenden Sie jederzeit sicher mit der Tastenkombination `STRG + C`.