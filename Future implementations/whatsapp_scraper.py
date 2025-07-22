from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
import speech_recognition as sr
import sqlite3
import re

edge_driver_path = "C:/Users/anasa/Downloads/edgedriver_win64/msedgedriver.exe"
edge_options = Options()
edge_options.add_argument("--start-maximized")

service = Service(edge_driver_path)
driver = webdriver.Edge(service=service, options=edge_options)

conn = sqlite3.connect('../flagged_messages.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS flagged_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT,
    type TEXT,
    reason TEXT
)
''')

def flag_message(text):
    suspicious_keywords = ['drug', 'sale', 'mdma', 'lsd', 'mephedrone', 'buy', 'narcotic']
    for keyword in suspicious_keywords:
        if re.search(rf'\b{keyword}\b', text, re.IGNORECASE):
            return True, f"Keyword found: {keyword}"
    return False, None

def process_audio(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data)
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google ASR service; {e}")
        return None

driver.get("https://web.whatsapp.com")
input("Please scan the QR code and press Enter...")

def monitor_messages():
    while True:
        messages = driver.find_elements_by_css_selector("div[class='_1Gy50']")
        for message in messages:
            text = message.text
            if text:
                flagged, reason = flag_message(text)
                if flagged:
                    print(f"Flagged message: {text} - Reason: {reason}")
                    cursor.execute("INSERT INTO flagged_messages (message, type, reason) VALUES (?, ?, ?)",
                                   (text, 'text', reason))
                    conn.commit()

monitor_messages()

conn.close()
driver.quit()
