import sqlite3

conn = sqlite3.connect('flagged_messages.db')
cursor = conn.cursor()

cursor.execute('DELETE FROM messages')
conn.commit()

conn.close()

print("Messages deleted successfully.")
