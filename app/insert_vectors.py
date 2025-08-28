import asyncio
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

import pandas as pd
import asyncpg 
from database.vector_store import VectorStore
import uuid
from app.config.settings import get_settings 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
CSV_FILE_PATH = "../data/law_faq_dataset.csv"
CSV_SEPARATOR = ";"

load_dotenv()

try:
    vec = VectorStore(database_url=(os.getenv('NEON_DB_CONNECTION_STRING')))
    logging.info("VectorStore initialized.")
    db_url = os.getenv("NEON_DB_CONNECTION_STRING")
    if not db_url:
        raise ValueError("Database service URL not found in settings.")
except Exception as e:
    logging.error(f"Failed during initialization: {e}", exc_info=True)
    exit(1)

# --- Data Preparation Function (prepare_record - unchanged) ---
async def prepare_record(row, row_number):
    question = row.get('question', 'N/A') # Use .get for safety
    answer = row.get('answer', 'N/A')
    category = row.get('category', 'Unknown') # Use .get for safety

    content = f"Question: {question}\nAnswer: {answer}"

    try:
        embedding = await vec.generate_embedding(content) #returns a list of floats
        await asyncio.sleep(0.1)
        logging.debug(f"Generated embedding for row {row_number}")

        record = {
            "id": str(uuid.uuid4()),
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
    prepared_records = [await prepare_record(row, index) for index, row in df.iterrows()]
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