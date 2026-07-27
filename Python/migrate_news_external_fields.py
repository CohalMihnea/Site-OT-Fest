from pathlib import Path
import os
import sqlite3


def get_db_path() -> str:
    env_path = os.getenv("SQLITE_DB_PATH")
    if env_path:
        return env_path
    return str(Path(__file__).resolve().parent / "festival.db")


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def main():
    db_path = get_db_path()
    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_posts'")
    if not cursor.fetchone():
        raise RuntimeError("Tabela news_posts nu există. Pornește aplicația o dată înainte de migrare.")

    if not column_exists(cursor, "news_posts", "external_url"):
        cursor.execute("ALTER TABLE news_posts ADD COLUMN external_url VARCHAR(500)")
        print("Added news_posts.external_url")
    else:
        print("news_posts.external_url already exists")

    if not column_exists(cursor, "news_posts", "external_button_label"):
        cursor.execute("ALTER TABLE news_posts ADD COLUMN external_button_label VARCHAR(120)")
        print("Added news_posts.external_button_label")
    else:
        print("news_posts.external_button_label already exists")

    conn.commit()
    conn.close()
    print("News external link migration completed.")


if __name__ == "__main__":
    main()
