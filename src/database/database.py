import hashlib, hmac, os, sqlite3
from pathlib import Path
from contextlib import contextmanager


ROOT = Path(__file__).resolve().parents[2]
DATABASE_FOLDER = ROOT / "data" / "database"
DATABASE_PATH = DATABASE_FOLDER / "wellbeing_system.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

PBKDF2_ITERATIONS = 100000


@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def add_columns(connection, table, columns):
    existing = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})")
    }

    for name, column_type in columns.items():
        if name not in existing:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {name} {column_type}"
            )


def create_database():
    DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)

    with connect() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        add_columns(connection, "users", {
            "consent_accepted": "INTEGER NOT NULL DEFAULT 0",
            "consent_accepted_at": "TEXT",
        })

        add_columns(connection, "check_ins", {
            "explanation": "TEXT",
            "recommendation": "TEXT",
            "image_name": "TEXT",
            "blink_rate": "REAL",
            "head_position": "TEXT",
            "speech_rate": "REAL",
            "disfluency_rate": "REAL",
            "lexical_variety": "REAL",
        })

    return DATABASE_PATH


# --------------------------------------------------
# Users
# --------------------------------------------------

def hash_password(password):
    salt = os.urandom(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )

    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password, stored_password):
    salt_text, hash_text = stored_password.split(":")
    salt = bytes.fromhex(salt_text)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )

    return hmac.compare_digest(
        password_hash.hex(),
        hash_text,
    )


def create_user(full_name, username, password):
    try:
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO users (full_name, username, password_hash)
                VALUES (?, ?, ?)
                """,
                (full_name, username, hash_password(password)),
            )

        return True

    except sqlite3.IntegrityError:
        return False


def authenticate_user(username, password):
    with connect() as connection:
        user = connection.execute(
            """
            SELECT id, full_name, username, password_hash, consent_accepted
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if user is None or not verify_password(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "username": user["username"],
        "consent_accepted": bool(user["consent_accepted"]),
    }


def save_consent(user_id):
    with connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET consent_accepted = 1,
                consent_accepted_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id,),
        )


# --------------------------------------------------
# Check-ins
# --------------------------------------------------

def save_check_in(user_id, result):
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO check_ins (
                user_id,
                input_type,
                transcript,
                text_score,
                audio_score,
                vision_score,
                strain_score,
                wellbeing_score,
                summary,
                explanation,
                recommendation,
                image_name,
                blink_rate,
                head_position,
                speech_rate,
                disfluency_rate,
                lexical_variety
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                result["recording_type"],
                result["transcript"],
                result["text_score"],
                result["audio_score"],
                result.get("vision_score"),
                result["strain_score"],
                result["wellbeing_score"],
                result["phrase"],
                result["explanation"],
                result["recommendation"],
                result["image_name"],
                result.get("blink_rate"),
                result.get("head_position"),
                result["speech_rate"],
                result["disfluency_rate"],
                result["lexical_variety"],
            ),
        )

        return cursor.lastrowid


def get_recent_scores(user_id, limit=7):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT wellbeing_score
            FROM check_ins
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [
        float(row["wellbeing_score"])
        for row in reversed(rows)
    ]


def get_check_in_count(user_id):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM check_ins
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    return int(row["total"])


# --------------------------------------------------
# Trends
# --------------------------------------------------

def get_month_check_ins(user_id, limit=31):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                date(current_row.created_at, 'localtime') AS date,
                current_row.wellbeing_score AS score,
                current_row.summary AS phrase
            FROM check_ins AS current_row
            WHERE current_row.user_id = ?
              AND current_row.id IN (
                  SELECT MAX(grouped_row.id)
                  FROM check_ins AS grouped_row
                  WHERE grouped_row.user_id = ?
                  GROUP BY date(grouped_row.created_at, 'localtime')
              )
            ORDER BY current_row.created_at DESC, current_row.id DESC
            LIMIT ?
            """,
            (user_id, user_id, limit),
        ).fetchall()

    return [
        {
            "date": row["date"],
            "day": row["date"][8:10],
            "score": float(row["score"]),
            "phrase": row["phrase"],
        }
        for row in reversed(rows)
    ]


def get_check_in_dates(user_id, year, month):
    month_key = f"{int(year):04d}-{int(month):02d}"

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT date(created_at, 'localtime') AS check_in_date
            FROM check_ins
            WHERE user_id = ?
              AND strftime('%Y-%m', created_at, 'localtime') = ?
            ORDER BY check_in_date
            """,
            (user_id, month_key),
        ).fetchall()

    return [
        row["check_in_date"]
        for row in rows
    ]


def get_check_in_for_date(user_id, date_text):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                datetime(created_at, 'localtime') AS created_at_local,
                input_type,
                transcript,
                text_score,
                audio_score,
                vision_score,
                strain_score,
                wellbeing_score,
                summary,
                explanation,
                recommendation,
                image_name,
                blink_rate,
                head_position,
                speech_rate,
                disfluency_rate,
                lexical_variety
            FROM check_ins
            WHERE user_id = ?
              AND date(created_at, 'localtime') = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (user_id, date_text),
        ).fetchone()

    return dict(row) if row else None