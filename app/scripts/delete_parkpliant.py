import os
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
LIMIT = 5

DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


if __name__ == "__main__":
    try:
        db_conn = psycopg2.connect(DATABASE_CONN_STR)
        cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        print("Connected to the database")

        try:
            # Define the delete query as a multi-step transaction
            delete_query = """
            BEGIN;

            -- 1. Delete from feature_url_path first (since it references provider directly)
            DELETE FROM feature_url_path
            USING provider
            WHERE feature_url_path.fk_provider_id = provider.id
              AND provider.name = 'Park Pliant';

            -- 2. Delete from provider_creds
            DELETE FROM provider_creds
            USING provider
            WHERE provider_creds.fk_provider_id = provider.id
              AND provider.name = 'Park Pliant';

            -- 3. Delete from provider_feature
            DELETE FROM provider_feature
            USING provider
            WHERE provider_feature.fk_provider_id = provider.id
              AND provider.name = 'Park Pliant';

            -- 4. Finally, delete from provider
            DELETE FROM provider
            WHERE name = 'Park Pliant';

            COMMIT;
            """

            # Execute the query
            cursor.execute(delete_query)
            db_conn.commit()  # Commit the transaction
            print("Data deleted successfully")

        except Exception as e:
            db_conn.rollback()  # Rollback if an error occurs
            print(f"Error occurred: {e}")

        finally:
            # Clean up resources: close cursor and connection
            cursor.close()
            db_conn.close()
            print("Connection closed")

    except Exception as e:
        print(f"Failed to connect to the database: {e}")
