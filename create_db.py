import sqlite3

conn = sqlite3.connect('students.db')
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    course TEXT NOT NULL,
    status TEXT,
    grade TEXT
)
""")

conn.commit()
conn.close()

print("Table created successfully")