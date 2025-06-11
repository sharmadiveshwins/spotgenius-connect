import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


provider_data = [
    {
        "provider_text_key": "t2",
        "provider_type": "payment",
        "provider_data_to_update": {
            "provider_api_request_type": "northstar",
            "api_request_endpoint": os.getenv("PAYMENT_SERVICE_BASE_URL")
        }
    }
]


if __name__ == "__main__":
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    try:
        for provider in provider_data:
            provider_text_key = provider["provider_text_key"]
            provider_type = provider["provider_type"]

            search_term = f"%{provider_type}%"
            cursor.execute(
                """
                SELECT
                    *
                FROM provider_types
                WHERE text_key ILIKE %s
                """,
                (search_term,)
            )

            provider_types_record = cursor.fetchone()
            if provider_types_record:
                search_term = f"%{provider_text_key}%"
                cursor.execute(
                    """
                    SELECT
                        *
                    FROM provider
                    WHERE
                        fk_provider_type_id = %s and
                        text_key ILIKE %s
                    """,
                    (provider_types_record['id'], search_term)
                )

                provider_record = cursor.fetchone()
                if provider_record:
                    cursor.execute(
                        """
                        UPDATE provider
                        SET
                            provider_api_request_type = %s,
                            api_request_endpoint = %s
                        WHERE
                            id = %s
                        """,
                        (
                            provider["provider_data_to_update"]["provider_api_request_type"],
                            provider["provider_data_to_update"]["api_request_endpoint"],
                            provider_record['id']
                        )
                    )

                    db_conn.commit()
                    print(f"Provider {provider_text_key} updated successfully")

        cursor.close()
        db_conn.close()
        print("Database connection closed")

    except Exception as e:
        print(f"Error: {e}")
        cursor.close()
        db_conn.close()
        print("Database connection closed")
