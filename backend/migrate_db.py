import sqlite3

def migrate():
    conn = sqlite3.connect('sql_app.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE captured_pokemons ADD COLUMN level INTEGER DEFAULT 5")
        cursor.execute("ALTER TABLE captured_pokemons ADD COLUMN xp INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE captured_pokemons ADD COLUMN base_exp INTEGER DEFAULT 50")
        cursor.execute("ALTER TABLE captured_pokemons ADD COLUMN species_url VARCHAR")
        conn.commit()
        print("Migration successful")
    except Exception as e:
        print("Migration error (maybe already applied?):", e)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
