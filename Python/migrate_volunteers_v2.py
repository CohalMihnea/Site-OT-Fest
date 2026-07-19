"""
Migrare sigură pentru noul sistem de ore voluntari.

Rulează o singură dată pe Render, fără să schimbi sau să ștergi festival.db:

    cd Python
    python migrate_volunteers_v2.py

Scriptul creează doar tabele noi dacă nu există deja.
Nu șterge conturi, înscrieri sau tabele existente.
"""

from sqlalchemy import text

from database import engine


TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS volunteer_profiles (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL UNIQUE,
        festival_departments TEXT,
        club_departments TEXT,
        created_at DATETIME NOT NULL,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_volunteer_profiles_id
    ON volunteer_profiles (id)
    """,
    """
    CREATE TABLE IF NOT EXISTS volunteer_invite_codes (
        id INTEGER PRIMARY KEY,
        code VARCHAR(20) NOT NULL UNIQUE,
        created_by_admin_id INTEGER NOT NULL,
        used_by_user_id INTEGER,
        created_at DATETIME NOT NULL,
        expires_at DATETIME NOT NULL,
        used_at DATETIME,
        FOREIGN KEY(created_by_admin_id) REFERENCES users(id),
        FOREIGN KEY(used_by_user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_volunteer_invite_codes_id
    ON volunteer_invite_codes (id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_volunteer_invite_codes_code
    ON volunteer_invite_codes (code)
    """,
    """
    CREATE TABLE IF NOT EXISTS volunteer_hour_codes (
        id INTEGER PRIMARY KEY,
        code VARCHAR(20) NOT NULL UNIQUE,
        event_type VARCHAR(50) NOT NULL,
        task VARCHAR(255) NOT NULL,
        work_date VARCHAR(20) NOT NULL,
        hours INTEGER NOT NULL,
        mentions TEXT,
        created_by_admin_id INTEGER NOT NULL,
        used_by_user_id INTEGER,
        created_hour_entry_id INTEGER,
        created_at DATETIME NOT NULL,
        expires_at DATETIME NOT NULL,
        used_at DATETIME,
        FOREIGN KEY(created_by_admin_id) REFERENCES users(id),
        FOREIGN KEY(used_by_user_id) REFERENCES users(id),
        FOREIGN KEY(created_hour_entry_id) REFERENCES volunteer_hour_entries(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_volunteer_hour_codes_id
    ON volunteer_hour_codes (id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_volunteer_hour_codes_code
    ON volunteer_hour_codes (code)
    """,
    """
    CREATE TABLE IF NOT EXISTS volunteer_hour_entries (
        id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        task VARCHAR(255) NOT NULL,
        work_date VARCHAR(20) NOT NULL,
        hours INTEGER NOT NULL,
        mentions TEXT,
        status VARCHAR(50) NOT NULL DEFAULT 'in_asteptare',
        admin_feedback TEXT,
        approval_type VARCHAR(50) NOT NULL DEFAULT 'manual',
        used_code VARCHAR(20),
        created_by_code_id INTEGER,
        approved_by_admin_id INTEGER,
        created_at DATETIME NOT NULL,
        updated_at DATETIME,
        reviewed_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(created_by_code_id) REFERENCES volunteer_hour_codes(id),
        FOREIGN KEY(approved_by_admin_id) REFERENCES users(id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_volunteer_hour_entries_id
    ON volunteer_hour_entries (id)
    """,
]


def main():
    with engine.begin() as connection:
        for sql in TABLES_SQL:
            connection.execute(text(sql))

    print("Migrarea voluntarilor v2 a fost aplicată cu succes.")


if __name__ == "__main__":
    main()
