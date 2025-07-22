import sqlite3
import logging
import instaloader
import spacy
from nltk import word_tokenize
from nltk.corpus import stopwords
import speech_recognition as sr
from pydub import AudioSegment

nlp = spacy.load('en_core_web_sm')
stop_words = set(stopwords.words('english'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KEYWORDS = ["mdma", "lsd", "mephedrone", "cocaine", "heroin", "ecstasy"]

conn = sqlite3.connect('flagged_instagram_posts.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    post TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

def preprocess_message(text):
    tokens = word_tokenize(text.lower())
    filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
    return ' '.join(filtered_tokens)

def nlp_analysis(text):
    doc = nlp(text)
    flagged_entities = [ent.text.lower() for ent in doc.ents if ent.label_ in ['DRUG', 'ORG', 'GPE']]
    return flagged_entities

def transcribe_audio(file_path):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(file_path)
    audio.export("temp.wav", format="wav")

    with sr.AudioFile("temp.wav") as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            logger.info(f"Transcription: {text}")
            return text
        except sr.UnknownValueError:
            logger.error("Google Speech Recognition could not understand the audio.")
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
    return ""

def scrape_instagram_posts(username):
    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(loader.context, username)

        for post in profile.get_posts():
            text = post.caption or ""
            logger.info(f"Post from {username}: {text}")

            preprocessed_text = preprocess_message(text)
            if any(keyword in preprocessed_text for keyword in KEYWORDS) or nlp_analysis(preprocessed_text):
                logger.info(f"Flagged post from {username}: {text}")

                cursor.execute('''
                INSERT INTO posts (username, post)
                VALUES (?, ?)
                ''', (username, text))
                conn.commit()

            if post.typename == "GraphVideo":
                file_path = f"{username}_{post.shortcode}.mp4"
                loader.download_post(post, target=file_path)
                transcribed_text = transcribe_audio(file_path)
                if transcribed_text:
                    preprocessed_text = preprocess_message(transcribed_text)
                    if any(keyword in preprocessed_text for keyword in KEYWORDS) or nlp_analysis(preprocessed_text):
                        logger.info(f"Flagged audio from {username}: {transcribed_text}")

                        cursor.execute('''
                        INSERT INTO posts (username, post)
                        VALUES (?, ?)
                        ''', (username, transcribed_text))
                        conn.commit()

    except Exception as e:
        logger.error(f"Error scraping Instagram: {e}")

if __name__ == '__main__':
    scrape_instagram_posts('target_username')
