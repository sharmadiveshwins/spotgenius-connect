import os
import psycopg2
import psycopg2.extras
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# PARKING_LOT_ID = 1837
# TIMESTAMP = '2025-03-21 12:00:00'
LIMIT = 5

DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


if __name__ == "__main__":
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        # sessions
        cursor.execute(
            f"""
            SELECT 
                id 
            FROM sessions 
            WHERE  
                deleted_at is not null
                ORDER BY deleted_at, created_at
            LIMIT {LIMIT};
        """
        )
        sessions_records = cursor.fetchall()
        sessions_records_ids = [record['id'] for record in sessions_records]
        print(f'Total {len(sessions_records_ids)} sessions records found')

        # task
        cursor.execute(
            f"""
            SELECT
                id
            FROM task
            WHERE
                session_id in {tuple(sessions_records_ids)};
        """
        )
        task_records = cursor.fetchall()
        task_records_ids = [record['id'] for record in task_records]
        print(f'Total {len(task_records_ids)} task records found')

        # violation
        cursor.execute(
            f"""
            DELETE
            FROM violation
            WHERE
                fk_task in {tuple(task_records_ids)};
        """
        )
        print(f'violation records marked to delete')

        # sub_task
        cursor.execute(
            f"""
            DELETE
            FROM sub_task
            WHERE
                fk_task in {tuple(task_records_ids)};
        """
        )
        print(f'sub_task records marked to delete')

        # session_log
        cursor.execute(
            f"""
            DELETE
            FROM session_log
            WHERE
                fk_sessions in {tuple(sessions_records_ids)};
        """
        )
        print(f'session_log records marked to delete')

        # delete from task
        cursor.execute(
            f"""
            DELETE
            FROM task
            WHERE
                id in {tuple(task_records_ids)};
        """
        )
        print(f'task records marked to delete')

        # delete from sessions
        cursor.execute(
            f"""
            DELETE
            FROM sessions
            WHERE
                id in {tuple(sessions_records_ids)};
        """
        )
        print(f'sessions records marked to delete')

        db_conn.commit()
        cursor.close()
        db_conn.close()
        print("Data deleted successfully")

    except Exception as e:
        print(f"Error: {e}")
        cursor.close()
        db_conn.close()
