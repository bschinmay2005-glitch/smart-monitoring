import sqlite3

DB_NAME = "attendance.db"

def connect():
    return sqlite3.connect(DB_NAME)
def create_table():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        student_id TEXT,
        date TEXT,
        time TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()