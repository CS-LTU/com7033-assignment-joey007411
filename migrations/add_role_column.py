import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), '../app/data/users.db')
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Add role column if it doesn't exist
        cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user' NOT NULL")
        conn.commit()
        print("✓ Added 'role' column to users table")
    except sqlite3.OperationalError as e:
        if 'duplicate column' in str(e):
            print("✓ Role column already exists")
        else:
            print(f"✗ Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
