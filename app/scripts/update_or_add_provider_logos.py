import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


load_dotenv()


DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").lower()

if ENVIRONMENT == "prod":
    LOGO_BASE_URL = "https://connect.spotgenius.com/api/v1/logo/"
elif ENVIRONMENT == "staging":
    LOGO_BASE_URL = "https://connect-stg.spotgenius.com/api/v1/logo/"
else:
    LOGO_BASE_URL = "https://connect-dev.spotgenius.com/api/v1/logo/"


provider_data = [
    {
        "provider_text_key": "arrive.parkwhiz",
        "provider_logo": "arrive-parkwhiz.png"
    },
    {
        "provider_text_key": "clancy",
        "provider_logo": "clancy.png"
    },
    {
        "provider_text_key": "dataticket",
        "provider_logo": "data-ticket.png"
    },
    {
        "provider_text_key": "flowbird.cale",
        "provider_logo": "flowbird.png"
    },
    {
        "provider_text_key": "global.permit",
        "provider_logo": "global.png"
    },
    {
        "provider_text_key": "integrapark.paris",
        "provider_logo": "paris.png"
    },
    {
        "provider_text_key": "oobeo.payment",
        "provider_logo": "oobeo-payment.png"
    },
    {
        "provider_text_key": "oobeo.enforce",
        "provider_logo": "oobeo-enforceplus.png"
    },
    {
        "provider_text_key": "parkmobile.payment",
        "provider_logo": "park-mobile.png"
    },
    {
        "provider_text_key": "Tiba",
        "provider_logo": "tiba-spark.png"
    },
    {
        "provider_text_key": "t2",
        "provider_logo": "t2-systems.png"
    },
    {
        "provider_text_key": "ventek",
        "provider_logo": "ventek.png"
    }
]


def update_provider_logo(provider_data):
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        for provider_dt in provider_data:
            text_key = provider_dt["provider_text_key"]
            logo_url = LOGO_BASE_URL + provider_dt["provider_logo"]

            cursor.execute("SELECT * FROM provider WHERE text_key = %s", (text_key,))
            provider = cursor.fetchone()

            if provider:
                print(f"Updating provider {text_key} with logo {logo_url}")
                cursor.execute(
                    "UPDATE provider SET logo = %s WHERE text_key = %s",
                    (logo_url, text_key)
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
    update_provider_logo(provider_data)
