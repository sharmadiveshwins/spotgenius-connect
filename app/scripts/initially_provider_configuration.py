import sys
import os
import json
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()



DATABASE_CONN_STR = os.getenv("SQLALCHEMY_DATABASE_URI")
assert DATABASE_CONN_STR is not None, "Please set env variable SQLALCHEMY_DATABASE_URI"


def get_table_structure(cursor, table_name, **kwargs):
    # Fetch column names, data types, and nullability for the table
    cursor.execute("""
        SELECT column_name, is_nullable, data_type
        FROM information_schema.columns
        WHERE table_name = %s
    """, (table_name,))
    columns = cursor.fetchall()

    # Build the JSON template from the structure
    template = {}
    for column in columns:
        col_name = column['column_name']
        is_nullable = column['is_nullable'] == 'YES'
        # Set default values based on column type and nullability
        # Handle JSON columns specially
        if is_nullable:
            template[col_name] = None  # Nullable fields default to None
        else:
            template[col_name] = ""  # Non-nullable fields default to empty string

    for key, value in kwargs.items():
        if key in template:
            template[key] = value  # Map the value from kwargs to the template

    return template


if __name__ == "__main__":
    print("Connecting to database...")
    db_conn = psycopg2.connect(DATABASE_CONN_STR)
    cursor = db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    print("Connected to database")

    # fetch all the option for text_key in provider table
    cursor.execute("SELECT text_key FROM provider_types ORDER BY text_key")
    rows = cursor.fetchall()

    print("\nAvailable option for provider type configuration:")
    for idx, row in enumerate(rows, 1):
        print(f"{idx}. {row['text_key']}")
    choice = input("Select text_key by number: ")

    provider_type_id = None
    feature_text_key = None

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(rows):
            provider_type_id = rows[idx - 1]['text_key']
        else:
            print("Invalid number. Exiting.")
            exit(1)

    print(f"✅ Using text_key: {provider_type_id}")

    # fetch all the option for feature from feature table to map feature with provider like payment or enforcement

    cursor.execute("SELECT text_key FROM feature ORDER BY text_key")
    rows = cursor.fetchall()

    print("\nAvailable option for feature configuration:")
    for idx, row in enumerate(rows, 1):
        print(f"{idx}. {row['text_key']}")
    choice = input("Select text_key by number: ")

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(rows):
            feature_text_key = rows[idx - 1]['text_key']
        else:
            print("Invalid number. Exiting.")
            exit(1)

    print(f"✅ Using text_key: {feature_text_key}")

    try:

        # fetch provider type

        cursor.execute(f"""
            
            SELECT id as provider_type_id from provider_types where text_key = %s             
        """, (provider_type_id,))

        fk_provider_type_id = cursor.fetchone()['provider_type_id']
        print(f"Provider type ID {fk_provider_type_id}")

        sample_data = get_table_structure(cursor, "provider", fk_provider_type_id=fk_provider_type_id)

        print("\n📝 Edit the JSON below with your values:")
        print(json.dumps(sample_data, indent=4))

        print("\nPaste updated JSON here (press Ctrl+D when done):\n")
        user_input = sys.stdin.read()
        data = json.loads(user_input)

        # Check for required fields
        final_values = []
        for column, value in data.items():
            if value is None and column not in sample_data:
                print(f"❌ '{column}' cannot be null, it is a required field.")
                exit(1)
            if isinstance(value, dict):
                final_values.append(json.dumps(value))
            else:
                final_values.append(value)


        insert_columns = tuple(data.keys())
        insert_values = tuple(final_values)

        # inert into provider table

        query = f"""
                INSERT INTO provider ({', '.join(insert_columns)})
                VALUES ({', '.join(['%s'] * len(insert_values))})
                RETURNING id AS provider_id;
                """

        cursor.execute(query, insert_values)
        provider_id = cursor.fetchone()['provider_id']
        print(f"Inserted provider with ID: {provider_id}")

        # fetch feature
        cursor.execute("""
                    SELECT id AS feature_id
                    FROM feature
                    WHERE text_key = %s;
                """, (feature_text_key,))

        feature_id = cursor.fetchone()['feature_id']
        print(f"Feature ID: {feature_id}")

        # Insert into provider feature table
        cursor.execute("""
                    INSERT INTO provider_feature (fk_provider_id, fk_feature)
                    VALUES (%s, %s)
                    RETURNING id AS provider_feature_id;
                """, (provider_id, feature_id))

        print("Inserted into  provider feature table successfully.")

        provider_feature_id = cursor.fetchone()['provider_feature_id']
        print(f"✅: user provider_feature_id = {provider_feature_id}")
        # Insert into feature url path table

        feature_url_path_sample_data = get_table_structure(cursor, "feature_url_path",
                                                           fk_provider_id=provider_id, fk_provider_feature=provider_feature_id)
        print("\n📝 Edit the JSON below with your values:")
        print(json.dumps(feature_url_path_sample_data, indent=4))

        print("\nPaste updated JSON here:\n")
        user_input = sys.stdin.read()
        data = json.loads(user_input)
        print(f"data-------------", data)
        # Check for required fields
        feature_url_path_final_values = []
        for column, value in data.items():
            if value is None and column not in sample_data:
                print(f"❌ '{column}' cannot be null, it is a required field.")
                exit(1)
            if isinstance(value, dict):
                value = json.dumps(value)  # Always ensure dicts are strings
            feature_url_path_final_values.append(value)


        feature_url_insert_columns = tuple(data.keys())
        feature_url_insert_values = tuple(feature_url_path_final_values)

        query = f"""
                INSERT INTO feature_url_path ({', '.join(feature_url_insert_columns)})
                VALUES ({', '.join(['%s'] * len(feature_url_insert_values))});"""

        print(f" inserting in url path {cursor.mogrify(query, feature_url_insert_values)}")
        # Execute query and fetch the returned provider_id
        cursor.execute(query, feature_url_insert_values)

        # Commit the transaction
        db_conn.commit()
        print("Inserted into feature url path table successfully.")


    except Exception as e:

        exc_type, exc_obj, tb = sys.exc_info()
        f_name = os.path.basename(tb.tb_frame.f_code.co_filename)
        line_number = tb.tb_lineno
        print(f"Error in {f_name} at line {line_number}: {e}")

        db_conn.rollback()

    finally:
        cursor.close()
        db_conn.close()