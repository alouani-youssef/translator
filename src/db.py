import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from src.config import Config


def get_connection():
    return psycopg2.connect(Config.DATABASE_URL)


@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def init_db():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS translation_operations (
                id                  SERIAL PRIMARY KEY,
                filename            TEXT        NOT NULL,
                property            TEXT        NOT NULL,
                value               TEXT        NOT NULL,
                language            TEXT        NOT NULL,
                translation         TEXT,
                translation_language TEXT,
                detected_input_lang TEXT,
                detected_output_lang TEXT,
                is_successed        BOOLEAN     DEFAULT FALSE,
                score               FLOAT       DEFAULT NULL,
                is_approved         BOOLEAN     DEFAULT FALSE,
                is_verified         BOOLEAN     DEFAULT FALSE,
                verified_at         TIMESTAMPTZ DEFAULT NULL,
                notes               TEXT        DEFAULT NULL,
                translation_time    FLOAT       DEFAULT NULL,
                input_size          INTEGER     DEFAULT NULL,
                output_size         INTEGER     DEFAULT NULL,
                size_difference     FLOAT       DEFAULT NULL,
                created_at          TIMESTAMPTZ DEFAULT NOW(),
                updated_at          TIMESTAMPTZ DEFAULT NOW(),
                CONSTRAINT idx_translations_unique UNIQUE (filename, property, language, translation_language)
            );

            -- Ensure constraints and new columns exist if table was created without them
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'idx_translations_unique') THEN
                    ALTER TABLE translation_operations ADD CONSTRAINT idx_translations_unique UNIQUE (filename, property, language, translation_language);
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='translation_operations' AND column_name='is_verified') THEN
                    ALTER TABLE translation_operations ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
                END IF;

                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='translation_operations' AND column_name='verified_at') THEN
                    ALTER TABLE translation_operations ADD COLUMN verified_at TIMESTAMPTZ DEFAULT NULL;
                END IF;
            END $$;

            CREATE OR REPLACE FUNCTION update_updated_at()
            RETURNS TRIGGER LANGUAGE plpgsql AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$;

            DROP TRIGGER IF EXISTS trg_translations_updated_at ON translation_operations;
            CREATE TRIGGER trg_translations_updated_at
                BEFORE UPDATE ON translation_operations
                FOR EACH ROW EXECUTE PROCEDURE update_updated_at();

            CREATE TABLE IF NOT EXISTS operations_logs (
                id                  SERIAL PRIMARY KEY,
                filename            TEXT,
                property            TEXT,
                value               TEXT,
                translation         TEXT,
                language            TEXT,
                translation_language TEXT,
                is_successed        BOOLEAN,
                translation_time    FLOAT,
                created_at          TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    print("✅ Database initialized")


def upsert_translation(
    filename: str,
    property: str,
    value: str,
    language: str,
    translation: str,
    translation_language: str,
    detected_input_lang: str = None,
    detected_output_lang: str = None,
    is_successed: bool = False,
    score: float = None,
    is_approved: bool = False,
    notes: str = None,
    translation_time: float = None,
    input_size: int = None,
    output_size: int = None,
    size_difference: float = None,
    is_verified: bool = False,
    verified_at = None,
):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO translation_operations
                (filename, property, value, language, translation, translation_language, 
                 detected_input_lang, detected_output_lang, is_successed, score, is_approved, 
                 is_verified, verified_at, notes, translation_time, input_size, output_size, size_difference)
            VALUES
                (%(filename)s, %(property)s, %(value)s, %(language)s, %(translation)s,
                 %(translation_language)s, %(detected_input_lang)s, %(detected_output_lang)s, 
                 %(is_successed)s, %(score)s, %(is_approved)s, %(is_verified)s, %(verified_at)s, %(notes)s, 
                 %(translation_time)s, %(input_size)s, %(output_size)s, %(size_difference)s)
            ON CONFLICT (filename, property, language, translation_language)
            DO UPDATE SET
                value                = EXCLUDED.value,
                translation          = EXCLUDED.translation,
                detected_input_lang  = EXCLUDED.detected_input_lang,
                detected_output_lang = EXCLUDED.detected_output_lang,
                is_successed         = EXCLUDED.is_successed,
                score                = EXCLUDED.score,
                is_approved          = EXCLUDED.is_approved,
                is_verified          = EXCLUDED.is_verified,
                verified_at          = EXCLUDED.verified_at,
                notes                = EXCLUDED.notes,
                translation_time     = EXCLUDED.translation_time,
                input_size           = EXCLUDED.input_size,
                output_size          = EXCLUDED.output_size,
                size_difference      = EXCLUDED.size_difference;

            INSERT INTO operations_logs
                (filename, property, value, translation, language, translation_language, is_successed, translation_time)
            VALUES
                (%(filename)s, %(property)s, %(value)s, %(translation)s, %(language)s, %(translation_language)s, %(is_successed)s, %(translation_time)s);
        """, {
            "filename": filename,
            "property": property,
            "value": value,
            "language": language,
            "translation": translation,
            "translation_language": translation_language,
            "detected_input_lang": detected_input_lang,
            "detected_output_lang": detected_output_lang,
            "is_successed": is_successed,
            "score": score,
            "is_approved": is_approved,
            "is_verified": is_verified,
            "verified_at": verified_at,
            "notes": notes,
            "translation_time": translation_time,
            "input_size": input_size,
            "output_size": output_size,
            "size_difference": size_difference,
        })


def bulk_upsert_translations(records: list[dict]):
    if not records:
        return

    with get_cursor() as cur:
        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO translation_operations
                (filename, property, value, language, translation, translation_language, 
                 detected_input_lang, detected_output_lang, is_successed, score, is_approved, 
                 is_verified, verified_at, notes, translation_time, input_size, output_size, size_difference)
            VALUES
                (%(filename)s, %(property)s, %(value)s, %(language)s, %(translation)s,
                 %(translation_language)s, %(detected_input_lang)s, %(detected_output_lang)s, 
                 %(is_successed)s, %(score)s, %(is_approved)s, %(is_verified)s, %(verified_at)s, %(notes)s, 
                 %(translation_time)s, %(input_size)s, %(output_size)s, %(size_difference)s)
            ON CONFLICT (filename, property, language, translation_language)
            DO UPDATE SET
                value                = EXCLUDED.value,
                translation          = EXCLUDED.translation,
                detected_input_lang  = EXCLUDED.detected_input_lang,
                detected_output_lang = EXCLUDED.detected_output_lang,
                is_successed         = EXCLUDED.is_successed,
                score                = EXCLUDED.score,
                is_approved          = EXCLUDED.is_approved,
                is_verified          = EXCLUDED.is_verified,
                verified_at          = EXCLUDED.verified_at,
                notes                = EXCLUDED.notes,
                translation_time     = EXCLUDED.translation_time,
                input_size           = EXCLUDED.input_size,
                output_size          = EXCLUDED.output_size,
                size_difference      = EXCLUDED.size_difference;
            """,
            records,
            page_size=100,
        )

        psycopg2.extras.execute_batch(
            cur,
            """
            INSERT INTO operations_logs
                (filename, property, value, translation, language, translation_language, is_successed, translation_time)
            VALUES
                (%(filename)s, %(property)s, %(value)s, %(translation)s, %(language)s, %(translation_language)s, %(is_successed)s, %(translation_time)s);
            """,
            records,
            page_size=100,
        )


def get_pending_validations(limit: int = 50):
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, value, translation, language, translation_language 
            FROM translation_operations 
            WHERE is_verified IS FALSE 
            ORDER BY created_at ASC 
            LIMIT %s;
        """, (limit,))
        return cur.fetchall()


def update_approval_status(record_id: int, is_approved: bool, notes: str = None):
    with get_cursor() as cur:
        cur.execute("""
            UPDATE translation_operations 
            SET is_approved = %s, 
                is_verified = TRUE, 
                verified_at = NOW(),
                notes = COALESCE(%s, notes) 
            WHERE id = %s;
        """, (is_approved, notes, record_id))

def get_approved_translations(texts: list[str], source_lang: str, target_lang: str) -> dict[str, str]:
    if not texts:
        return {}
    
    with get_cursor() as cur:
        cur.execute("""
            SELECT value, translation 
            FROM translation_operations 
            WHERE value = ANY(%s) 
              AND language = %s 
              AND translation_language = %s 
              AND is_successed = TRUE 
              AND is_approved = TRUE
        """, (texts, source_lang, target_lang))
        return {row['value']: row['translation'] for row in cur.fetchall()}
