import sqlite3
import logging
import speech_recognition as sr
from pydub import AudioSegment
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from PIL import Image
import io
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_TOKEN = ("7438304286:AAGSaFZz1aGgy6xqtAvQ4vUWOW9HoAkQIfM")

conn = sqlite3.connect('flagged_messages.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    user TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

messages = [
    "I love this game!",
    "Buy LSD here, fast delivery!",
    "Just had a great meal!",
    "MDMA available for sale",
    "Looking for party drugs?, drug needed,ca",
    "Amazing weather today!",
    "Get your alcohol here!, alcoholic products, MDMA needed",
    "Need prescription medicine",
    "Best places to eat out",
    "Cocaine on sale now",
    "New workout routine",
]

labels = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0]

X_train, X_test, y_train, y_test = train_test_split(messages, labels, test_size=0.2, random_state=42)

model_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('classifier', LogisticRegression())
])

model_pipeline.fit(X_train, y_train)
print("Model trained successfully!")

def classify_text(text: str) -> bool:
    prediction = model_pipeline.predict([text])
    return prediction[0] == 1

async def transcribe_voice_message(file_path: str) -> str:
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            logger.info(f"Transcribed voice message: {text}")
            return text
        except sr.UnknownValueError:
            logger.error("Google Speech Recognition could not understand the audio.")
            return ""
        except sr.RequestError as e:
            logger.error(f"Could not request results from Google Speech Recognition service; {e}")
            return ""

async def process_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    photo_file = await update.message.photo[-1].get_file()
    file_path = "received_image.jpg"
    await photo_file.download_to_drive(file_path)

    try:
        image = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(image)
        logger.info(f"Extracted text from image: {extracted_text}")
        return extracted_text
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}")
        return ""

async def flag_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        message_text = ""
        user = "unknown"
        chat_id = None
        is_voice_message = False
        is_image_message = False

        if update.message:
            if update.message.text:
                message_text = update.message.text.lower()
                user = update.message.from_user.username or "unknown"
                chat_id = update.message.chat_id
            elif update.message.voice:
                is_voice_message = True
                user = update.message.from_user.username or "unknown"
                chat_id = update.message.chat_id

                voice_file = await update.message.voice.get_file()
                file_path = "voice_message.ogg"
                await voice_file.download_to_drive(file_path)

                audio = AudioSegment.from_ogg(file_path)
                audio.export("voice_message.wav", format="wav")

                message_text = await transcribe_voice_message("voice_message.wav")

            elif update.message.photo:
                is_image_message = True
                user = update.message.from_user.username or "unknown"
                chat_id = update.message.chat_id

                message_text = await process_image(update, context)

        elif update.channel_post:
            if update.channel_post.text:
                message_text = update.channel_post.text.lower()
                user = "Channel"
                chat_id = update.channel_post.chat_id

        if message_text and classify_text(message_text):
            logger.info(f"Flagged message from {user}: {message_text}")

            cursor.execute('''
            INSERT INTO messages (chat_id, user, message)
            VALUES (?, ?, ?)
            ''', (chat_id, user, message_text))
            conn.commit()

            if is_voice_message:
                await update.message.reply_text("⚠️ Your voice message has been flagged for review.")
            elif is_image_message:
                await update.message.reply_text("⚠️ Your image has been flagged for review.")
            elif update.message and update.message.text:
                await update.message.reply_text("⚠️ Your message has been flagged for review.")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Bot is now monitoring the channel for flagged keywords and images.')

def main():
    if not TELEGRAM_API_TOKEN:
        logger.error("Telegram API Token is not set. Please check your script.")
        return

    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, flag_message))
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, flag_message))
    application.add_handler(MessageHandler(filters.VOICE, flag_message))
    application.add_handler(MessageHandler(filters.PHOTO, flag_message))

    logger.info("Starting the bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
