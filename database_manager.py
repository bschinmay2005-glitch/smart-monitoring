import sqlite3

# Using your file name
DB_NAME = "attendance.db"

def build_multi_table_database():
    """Creates multiple independent tables inside the SAME database file."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # TABLE 1: Displays Student Profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            class_name TEXT
        )
    ''')
    
    # TABLE 2: Displays Teacher Profiles 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            college_code TEXT NOT NULL
        )
    ''')
    
    # TABLE 3: Displays Live Attendance Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT DEFAULT 'Present'
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Success! Your '{DB_NAME}' file now contains 3 separate tables.")

if __name__ == "__main__":
    build_multi_table_database()