import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


text_key_dict = {
    'Admin Fake': 'admin.fake',
    'Arrive': 'arrive.parkwhiz',
    'DataTicket': 'dataticket',
    'Global': 'global.permit',
    'Oobeo': 'oobeo.payment',
    'Oobeo Enforcement': 'oobeo.enforce',
    'ParkMobile': 'parkmobile.payment',
    'T2': 't2',
    'adminFake': 'admin.fake',
    'arrive': 'arrive.parkwhiz',
    'clancy': 'clancy',
    'dataTicket': 'dataticket',
    'flowbird': 'flowbird.cale',
    'global': 'global.permit',
    'integrapark.paris': 'integrapark.paris',
    'oobeo': 'oobeo.payment',
    'oobeoEnforcement': 'oobeo.enforce',
    'parkMobile': 'parkmobile.payment',
    'spothero': 'spothero',
    't2': 't2',
    'ventek': 'ventek'
}


if __name__ == "__main__":
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        sql_lines = ["UPDATE provider", "SET text_key = CASE text_key"]
        for old_val, new_val in text_key_dict.items():
            sql_lines.append(f"    WHEN '{old_val}' THEN '{new_val}'")
        sql_lines.append("    ELSE text_key")
        sql_lines.append("END;")

        sql_query = "\n".join(sql_lines)

        cursor.execute(sql_query)
        db_conn.commit()
        print(f"Provider text keys updated successfully")

        cursor.close()
        db_conn.close()
        print("Database connection closed")

    except Exception as e:
        print(f"Error: {e}")
        cursor.close()
        db_conn.close()
        print("Database connection closed")
