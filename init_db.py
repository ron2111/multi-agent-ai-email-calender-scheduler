import sqlite3

def init_db():
    conn = sqlite3.connect('scheduler.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        preferences TEXT
    );
    ''')
    
    # Create meetings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        attendees TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('scheduled', 'rescheduled', 'canceled'))
    );
    ''')
    
    # Create feedback table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER,
        rating INTEGER CHECK(rating >=1 AND rating <=5),
        comments TEXT,
        FOREIGN KEY(meeting_id) REFERENCES meetings(id)
    );
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
