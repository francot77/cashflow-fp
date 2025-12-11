import sqlite3

DATABASE = "cashflow.db"

def init_db():
    conn = sqlite3.connect(DATABASE)
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print("DB inicializada en", DATABASE)

if __name__ == "__main__":
    init_db()