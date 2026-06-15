import sqlite3
import os

print("Current folder:", os.getcwd())

conn = sqlite3.connect("test.db")
conn.close()

print("Database created")