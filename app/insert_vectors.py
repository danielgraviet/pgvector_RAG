import asyncio
import logging
from datetime import datetime
import json

import pandas as pd
import asyncpg # <<< Add asyncpg import
from database.vector_store import VectorStore
from timescale_vector.client import uuid_from_time
# --- Assuming get_settings provides the database URL ---
from app.config.settings import get_settings # <<< Add settings import

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
CSV_FILE_PATH = "../data/law_faq_dataset.csv"
CSV_SEPARATOR = ";"

# --- Initialization ---
try:
    vec = VectorStore()
    logging.info("VectorStore initialized.")
    settings = get_settings() # <<< Get settings for DB URL
    db_url = settings.database.service_url # <<< Store DB URL
    if not db_url:
        raise ValueError("Database service URL not found in settings.")
except Exception as e:
    logging.error(f"Failed during initialization: {e}", exc_info=True)
    exit(1)

# --- Data Preparation Function (prepare_record - unchanged) ---
def prepare_record(row, row_number):
    # ... (keep existing prepare_record function) ...
    question = row.get('question', 'N/A') # Use .get for safety
    answer = row.get('answer', 'N/A')
    category = row.get('category', 'Unknown') # Use .get for safety

    content = f"Question: {question}\nAnswer: {answer}"

    try:
        embedding = vec.get_embedding(content)
        logging.debug(f"Generated embedding for row {row_number}")

        record = {
            "id": str(uuid_from_time(datetime.now())),
            "metadata": {
                "category": category,
                "source_row": row_number,
                "created_at": datetime.now().isoformat(),
            },
            "contents": content,
            "embedding": embedding,
        }
        return pd.Series(record)

    except Exception as e:
        logging.error(f"Error processing row {row_number} (Question: '{question[:50]}...'): {e}", exc_info=True)
        return None

# --- Main Asynchronous Function ---
async def main():
    logging.info(f"Reading data from {CSV_FILE_PATH}...")
    try:
        df = pd.read_csv(CSV_FILE_PATH, sep=CSV_SEPARATOR)
        logging.info(f"Successfully read {len(df)} rows from CSV.")
    except FileNotFoundError:
        logging.error(f"Error: CSV file not found at {CSV_FILE_PATH}")
        return
    except Exception as e:
        logging.error(f"Error reading CSV file {CSV_FILE_PATH}: {e}", exc_info=True)
        return

    logging.info("Preparing records for insertion...")
    prepared_records = [prepare_record(row, index) for index, row in df.iterrows()]
    valid_records = [r for r in prepared_records if r is not None]

    if not valid_records:
        logging.warning("No valid records were prepared after processing the CSV.")
        return

    records_df = pd.DataFrame(valid_records)
    logging.info(f"Successfully prepared {len(records_df)} valid records for insertion.")

    conn = None # Initialize conn outside try block
    try:
        logging.info("Ensuring database table exists...")
        await vec.create_tables()
        logging.info("Table check/creation complete.")

        logging.info("Ensuring database index exists...")
        await vec.create_index()
        logging.info("Index check/creation complete.")

        logging.info(f"Starting upsert operation for {len(records_df)} records via VectorStore...")
        await vec.upsert(records_df)
        logging.info("VectorStore upsert call finished.") # Renamed log slightly

        # --- vvv MANUAL INSERT TEST vvv ---
        logging.info("Attempting manual insert test using asyncpg...")
        conn = await asyncpg.connect(db_url) # Use the URL from settings
        logging.info("Manual connection successful.")
        async with conn.transaction(): # Start an explicit transaction
             # Generate a dummy embedding (replace 1536 with your actual dimension if different)
             dummy_embedding_list = [0.0] * vec.vector_settings.embedding_dimensions
             dummy_embedding_str = str(dummy_embedding_list)
             metadata_dict = {'manual_test': True, 'created_at': datetime.now().isoformat()} # Prepare dict
             await conn.execute(
                 """
                 INSERT INTO public.embeddings (id, metadata, contents, embedding)
                 VALUES ($1, $2, $3, $4)
                 """,
                 uuid_from_time(datetime.now()), # Generate new UUID
                 json.dumps(metadata_dict), 
                 'Manual test content', # Sample content
                 dummy_embedding_str # Sample embedding
             )
             logging.info("Manual insert executed within transaction.")
        # Transaction is automatically committed upon exiting 'async with' block without error
        logging.info("Manual insert transaction committed.")
        # --- ^^^ MANUAL INSERT TEST ^^^ ---
    except Exception as e:
        logging.error(f"An error occurred during database operations or manual test: {e}", exc_info=True)
    finally:
        if conn: # <<< Close manual connection if opened
             await conn.close()
             logging.info("Manual asyncpg connection closed.")


# --- Script Execution ---
if __name__ == "__main__":
    logging.info("Starting vector insertion script...")
    try:
        asyncio.run(main())
    except Exception as e:
        logging.critical(f"A critical error occurred during script execution: {e}", exc_info=True)
    finally:
        logging.info("Vector insertion script finished.")