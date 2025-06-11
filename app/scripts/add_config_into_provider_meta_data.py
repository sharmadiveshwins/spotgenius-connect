import os
import psycopg2
import psycopg2.extras
import json
from dotenv import load_dotenv

load_dotenv()


DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"

PROVIDER_TEXT_KEY = 'flowbird.cale'  # The text_key for which to update the data
CONFIG_LEVEL = 'parking_lot_level_config'   # give one of these ("global_level_config", "customer_level_config", "parking_lot_level_config")
CONFIG_JSON = '''{
    "key": "facility_id",
    "label": "Terminal Groups",
    "type": "text",
    "value": null
}'''


def update_metadata(provider_text_key, new_config_json):
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        cursor.execute("SELECT meta_data FROM provider WHERE text_key = %s;", (provider_text_key,))
        result = cursor.fetchone()
        if result:
            existing_data = result["meta_data"]
            new_config = json.loads(new_config_json)

            if CONFIG_LEVEL not in existing_data:
                existing_data[f"{CONFIG_LEVEL}"] = []

            existing_data[f"{CONFIG_LEVEL}"].append(new_config)
            cursor.execute(
                "UPDATE provider SET meta_data = %s WHERE text_key = %s;",
                (psycopg2.extras.Json(existing_data), provider_text_key)
            )

            db_conn.commit()
            print(f"Metadata updated successfully for text_key {provider_text_key}")
        else:
            print(f"No provider found with the given text_key: {provider_text_key}")

    except Exception as e:
        print(f"Error: {e}")
        db_conn.rollback()

    finally:
        cursor.close()
        db_conn.close()
        print("Database connection closed")


if __name__ == "__main__":
    provider_text_key = PROVIDER_TEXT_KEY
    update_metadata(provider_text_key, CONFIG_JSON)
