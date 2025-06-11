import os
import psycopg2
import psycopg2.extras
from datetime import timedelta
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable DATABASE_CONN_STR"


if __name__ == "__main__":
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        time_threshold = datetime.utcnow() - timedelta(hours=1)

        cursor.execute (
            f"""
                SELECT s.id, s.parking_lot_id
                FROM sessions s
                WHERE s.is_active = TRUE
                AND s.created_at < %s
                AND s.deleted_at IS NULL
                AND EXISTS (
                    SELECT 1 
                    FROM session_log sl
                    WHERE sl.fk_sessions = s.id
                    GROUP BY sl.fk_sessions
                    HAVING COUNT(*) = 1
                )
            """,
            (time_threshold,)
        )
        deleted_sessions = cursor.fetchall()
        deleted_session_ids = [record['id'] for record in deleted_sessions]
        print(f"soft deleted sessions ids {deleted_session_ids}")
        print(f'Total {len(deleted_session_ids)} session records found')


        cursor.execute(
            f"""
                UPDATE sessions us SET deleted_at = %s Where us.id in 
                (
                    SELECT s.id
                    FROM sessions s
                    WHERE s.is_active = TRUE
                    AND s.created_at < %s
                    AND s.deleted_at IS NULL
                    AND EXISTS (
                        SELECT 1 
                        FROM session_log sl
                        WHERE sl.fk_sessions = s.id
                        GROUP BY sl.fk_sessions
                        HAVING COUNT(*) = 1
                    )
                )
            """,
            (datetime.utcnow(), time_threshold)
        )

        db_conn.commit()
        cursor.close()
        db_conn.close()
        print("Sessions soft deleted successfully.")


    except Exception as e:
        print(f"Error: {e}")
        cursor.close()
        db_conn.close()
