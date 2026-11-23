import sqlite3

DB_PATH = "macave.db"

# Ouvre une connexion à la base SQLite
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par leur nom
    conn.execute("PRAGMA foreign_keys = ON;")  # Active les clés étrangères
    return conn

# Crée les tables à partir du fichier schema.sql
def init_db():
    conn = get_connection()
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()