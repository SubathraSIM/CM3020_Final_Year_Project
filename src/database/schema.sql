CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    consent_accepted INTEGER NOT NULL DEFAULT 0,
    consent_accepted_at TEXT
);

CREATE TABLE IF NOT EXISTS check_ins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    input_type TEXT NOT NULL
        CHECK (input_type IN ('audio', 'video')),

    transcript TEXT NOT NULL,

    text_score REAL NOT NULL,
    audio_score REAL NOT NULL,
    vision_score REAL,

    strain_score REAL NOT NULL,
    wellbeing_score REAL NOT NULL,

    blink_rate REAL,
    head_position TEXT,
    speech_rate REAL NOT NULL,
    disfluency_rate REAL NOT NULL,
    lexical_variety REAL NOT NULL,

    summary TEXT NOT NULL,
    explanation TEXT,
    recommendation TEXT,
    recommendation_source TEXT,
    image_name TEXT,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_check_ins_user_date
ON check_ins(user_id, created_at);