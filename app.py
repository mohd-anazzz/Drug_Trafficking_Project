from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

def get_flagged_messages():
    conn = sqlite3.connect('flagged_messages.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages")
    return cursor.fetchall()

@app.route('/')
def index():
    messages = get_flagged_messages()
    return render_template('index.html', messages=messages)

if __name__ == '__main__':
    app.run(debug=True)
