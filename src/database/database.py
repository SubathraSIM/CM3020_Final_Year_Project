import hashlib, hmac, os, sqlite3
from pathlib import Path
from contextlib import contextmanager
ROOT = Path(__file__).resolve().parents[2]
DATABASE_FOLDER = ROOT / 'data' / 'database'
DATABASE_PATH = DATABASE_FOLDER / 'wellbeing_system.db'
SCHEMA_PATH = Path(__file__).resolve().parent / 'schema.sql'
PBKDF2_ITERATIONS = 100000

@contextmanager
def connect():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def add_columns(connection, table, columns):
    existing = {row['name'] for row in connection.execute(f'PRAGMA table_info({table})')}
    for name, column_type in columns.items():
        if name not in existing:
            connection.execute(f'ALTER TABLE {table} ADD COLUMN {name} {column_type}')

def create_database():
    DATABASE_FOLDER.mkdir(parents=True, exist_ok=True)
    with connect() as connection:
        connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
        add_columns(connection, 'users', {'consent_accepted': 'INTEGER NOT NULL DEFAULT 0', 'consent_accepted_at': 'TEXT'})
        add_columns(connection, 'check_ins', {'original_language': "TEXT NOT NULL DEFAULT 'English'", 'transcript_original': 'TEXT', 'explanation': 'TEXT', 'recommendation': 'TEXT', 'image_name': 'TEXT', 'blink_rate': 'REAL', 'head_position': 'TEXT', 'speech_rate': 'REAL', 'disfluency_rate': 'REAL', 'lexical_variety': 'REAL'})
    return DATABASE_PATH

def hash_password(password):
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return f'{salt.hex()}:{password_hash.hex()}'

def verify_password(password, stored_password):
    salt_text, hash_text = stored_password.split(':')
    salt = bytes.fromhex(salt_text)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(password_hash.hex(), hash_text)

def create_user(full_name, username, password):
    try:
        with connect() as connection:
            connection.execute('\n                INSERT INTO users (full_name, username, password_hash)\n                VALUES (?, ?, ?)\n                ', (full_name, username, hash_password(password)))
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    with connect() as connection:
        user = connection.execute('\n            SELECT id, full_name, username, password_hash, consent_accepted\n            FROM users\n            WHERE username = ?\n            ', (username,)).fetchone()
    if user is None or not verify_password(password, user['password_hash']):
        return None
    return {'id': user['id'], 'full_name': user['full_name'], 'username': user['username'], 'consent_accepted': bool(user['consent_accepted'])}

def save_consent(user_id):
    with connect() as connection:
        connection.execute('\n            UPDATE users\n            SET consent_accepted = 1,\n                consent_accepted_at = CURRENT_TIMESTAMP\n            WHERE id = ?\n            ', (user_id,))

def save_check_in(user_id, result):
    with connect() as connection:
        existing = connection.execute("\n            SELECT id\n            FROM check_ins\n            WHERE user_id = ?\n              AND date(created_at, 'localtime')\n                  = date('now', 'localtime')\n            ORDER BY created_at DESC, id DESC\n            LIMIT 1\n            ", (user_id,)).fetchone()
        values = (result['recording_type'], result['language'], result['transcript'], result['transcript_english'], result['text_score'], result['audio_score'], result.get('vision_score'), result['strain_score'], result['wellbeing_score'], result['phrase_english'], result['explanation_english'], result['recommendation_english'], result['image_name'], result.get('blink_rate'), result.get('head_position'), result['speech_rate'], result['disfluency_rate'], result['lexical_variety'])
        if existing:
            connection.execute('\n                UPDATE check_ins\n                SET\n                    created_at = CURRENT_TIMESTAMP,\n                    input_type = ?,\n                    original_language = ?,\n                    transcript_original = ?,\n                    transcript = ?,\n                    text_score = ?,\n                    audio_score = ?,\n                    vision_score = ?,\n                    strain_score = ?,\n                    wellbeing_score = ?,\n                    summary = ?,\n                    explanation = ?,\n                    recommendation = ?,\n                    image_name = ?,\n                    blink_rate = ?,\n                    head_position = ?,\n                    speech_rate = ?,\n                    disfluency_rate = ?,\n                    lexical_variety = ?\n                WHERE id = ?\n                ', values + (existing['id'],))
            return existing['id']
        cursor = connection.execute('\n            INSERT INTO check_ins (\n                user_id,\n                input_type,\n                original_language,\n                transcript_original,\n                transcript,\n                text_score,\n                audio_score,\n                vision_score,\n                strain_score,\n                wellbeing_score,\n                summary,\n                explanation,\n                recommendation,\n                image_name,\n                blink_rate,\n                head_position,\n                speech_rate,\n                disfluency_rate,\n                lexical_variety\n            )\n            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n            ', (user_id,) + values)
        return cursor.lastrowid

def get_recent_scores(user_id, limit=7):
    with connect() as connection:
        rows = connection.execute('\n            SELECT wellbeing_score\n            FROM check_ins\n            WHERE user_id = ?\n            ORDER BY created_at DESC, id DESC\n            LIMIT ?\n            ', (user_id, limit)).fetchall()
    return [float(row['wellbeing_score']) for row in reversed(rows)]

def get_previous_scores(user_id, limit=30):
    """Return the user's past wellbeing scores, oldest first,
    for computing a personal baseline. Excludes nothing here —
    the caller decides how to use them relative to the current check-in."""
    with connect() as connection:
        rows = connection.execute('\n            SELECT wellbeing_score\n            FROM check_ins\n            WHERE user_id = ?\n            ORDER BY created_at DESC, id DESC\n            LIMIT ?\n            ', (user_id, limit)).fetchall()
    return [float(row['wellbeing_score']) for row in reversed(rows)]

def get_check_in_count(user_id):
    with connect() as connection:
        row = connection.execute('\n            SELECT COUNT(*) AS total\n            FROM check_ins\n            WHERE user_id = ?\n            ', (user_id,)).fetchone()
    return int(row['total'])

def get_month_check_ins(user_id, limit=31):
    with connect() as connection:
        rows = connection.execute("\n            SELECT\n                date(current_row.created_at, 'localtime') AS date,\n                current_row.wellbeing_score AS score,\n                current_row.summary AS phrase\n            FROM check_ins AS current_row\n            WHERE current_row.user_id = ?\n              AND current_row.id IN (\n                  SELECT MAX(grouped_row.id)\n                  FROM check_ins AS grouped_row\n                  WHERE grouped_row.user_id = ?\n                  GROUP BY date(grouped_row.created_at, 'localtime')\n              )\n            ORDER BY current_row.created_at DESC, current_row.id DESC\n            LIMIT ?\n            ", (user_id, user_id, limit)).fetchall()
    return [{'date': row['date'], 'day': row['date'][8:10], 'score': float(row['score']), 'phrase': row['phrase']} for row in reversed(rows)]

def get_check_in_dates(user_id, year, month):
    month_key = f'{int(year):04d}-{int(month):02d}'
    with connect() as connection:
        rows = connection.execute("\n            SELECT DISTINCT date(created_at, 'localtime') AS check_in_date\n            FROM check_ins\n            WHERE user_id = ?\n              AND strftime('%Y-%m', created_at, 'localtime') = ?\n            ORDER BY check_in_date\n            ", (user_id, month_key)).fetchall()
    return [row['check_in_date'] for row in rows]

def get_check_in_for_date(user_id, date_text):
    with connect() as connection:
        row = connection.execute("\n            SELECT\n                id,\n                datetime(created_at, 'localtime') AS created_at_local,\n                input_type,\n                original_language,\n                transcript_original,\n                transcript,\n                text_score,\n                audio_score,\n                vision_score,\n                strain_score,\n                wellbeing_score,\n                summary,\n                explanation,\n                recommendation,\n                image_name,\n                blink_rate,\n                head_position,\n                speech_rate,\n                disfluency_rate,\n                lexical_variety\n            FROM check_ins\n            WHERE user_id = ?\n              AND date(created_at, 'localtime') = ?\n            ORDER BY created_at DESC, id DESC\n            LIMIT 1\n            ", (user_id, date_text)).fetchone()
    return dict(row) if row else None

def delete_user(user_id):
    with connect() as connection:
        cursor = connection.execute('\n            DELETE FROM users\n            WHERE id = ?\n            ', (user_id,))
        return cursor.rowcount == 1