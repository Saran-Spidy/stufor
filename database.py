import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            age INTEGER,
            location TEXT,
            college TEXT,
            department TEXT,
            year TEXT,
            experience_level TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_name TEXT UNIQUE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS student_roles (
            student_id INTEGER,
            role_id INTEGER
        )
    """)

    # Insert predefined roles
    roles_list = [
        "Photographer",
        "Data Entry",
        "Welder",
        "Cameraman",
        "Catering Service",
        "Cook",
        "Home Mover",
        "Receptionist",
        "Anchor",
        "DJ",
        "Decorator"
    ]

    for role in roles_list:
        try:
            c.execute("INSERT INTO roles (role_name) VALUES (?)", (role,))
        except:
            pass


    # Jobs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            pay INTEGER,
            required_count INTEGER,
            expiry_time TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    # Applications table
    c.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            job_id INTEGER,
            status TEXT DEFAULT 'Applied',
            rating INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
