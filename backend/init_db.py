import sqlite3

def init_sqlite_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Create the users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )
    ''')

    # Create the vacancies table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vacancies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        school_name TEXT NOT NULL,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()
    print("SQLite database initialized successfully!")

if __name__ == '__main__':
    init_sqlite_db()
