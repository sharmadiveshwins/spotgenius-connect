import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


load_dotenv()


DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


provider_data = [
    {
        "provider_text_key": "arrive.parkwhiz",
        "provider_name": "Arrive (ParkWhiz)"
    },
    {
        "provider_text_key": "clancy",
        "provider_name": "Clancy Systems Inc"
    },
    {
        "provider_text_key": "dataticket",
        "provider_name": "Data Ticket"
    },
    {
        "provider_text_key": "flowbird.cale",
        "provider_name": "Flowbird - Cale"
    },
    {
        "provider_text_key": "global.permit",
        "provider_name": "Global Parking Solutions"
    },
    {
        "provider_text_key": "integrapark.paris",
        "provider_name": "PARIS"
    },
    {
        "provider_text_key": "oobeo.enforce",
        "provider_name": "Oobeo EnforcePlus"
    },
    {
        "provider_text_key": "parkmobile.payment",
        "provider_name": "ParkMobile"
    },
    {
        "provider_text_key": "Tiba",
        "provider_name": "TIBA"
    },
    {
        "provider_text_key": "t2",
        "provider_name": "T2 Systems"
    },
    {
        "provider_text_key": "ventek",
        "provider_name": "VenTek"
    }
]


def update_provider_names(provider_data):
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        for provider_dt in provider_data:
            text_key = provider_dt["provider_text_key"]
            name = provider_dt["provider_name"]

            cursor.execute("SELECT * FROM provider WHERE text_key = %s", (text_key,))
            provider = cursor.fetchone()

            if provider:
                print(f"Updating provider {text_key} with name {name}")
                cursor.execute(
                    "UPDATE provider SET name = %s WHERE text_key = %s",
                    (name, text_key)
                )
            else:
                print(f"Provider with text_key '{text_key}' not found.")
            db_conn.commit()

    except Exception as e:
        print(f"Error: {e}")
        db_conn.rollback()

    finally:
        cursor.close()
        db_conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    update_provider_names(provider_data)
