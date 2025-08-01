import logging
import time
from typing import Any, List, Optional, Tuple, Union
from datetime import datetime

import pandas as pd
import asyncpg
from app.config.settings import get_settings
from openai import OpenAI
from timescale_vector import client

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VectorStore:
    """A class for managing vector operations and database interactions."""

    def __init__(self):
        """Initialize the VectorStore with settings, OpenAI client, and Timescale Vector client."""
        self.settings = get_settings()
        self.openai_client = OpenAI(api_key=self.settings.openai.api_key)
        self.embedding_model = self.settings.openai.embedding_model
        self.vector_settings = self.settings.vector_store
        try:
            self.vec_client = client.Async(
                self.settings.database.service_url,
                self.vector_settings.table_name,
                self.vector_settings.embedding_dimensions,
                time_partition_interval=self.vector_settings.time_partition_interval,
            )
            logger.info("timescale vector client init success")
        except Exception as e:
            logger.error(f"Failed to initialize Timescale Vector client: {e}", exc_info=True)
            raise
            
    def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for the given text.

        Args:
            text: The input text to generate an embedding for.

        Returns:
            A list of floats representing the embedding.
        """
        
        if len(text.strip()) == 0:
            raise ValueError("Input text cannot be empty.")
                    
        text = text.replace("\n", " ")
        start_time = time.time() # cool function here that tracks the time for a function call. 
        embedding = (
            self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_model,
            )
            .data[0]
            .embedding
        )
        elapsed_time = time.time() - start_time # end of timer
        logging.info(f"Embedding generated in {elapsed_time:.3f} seconds") # output timer. 
        return embedding

    async def create_tables(self, table_name="embeddings"):
        """Creates the necessary tables in the database if they don't exist."""
        logging.info(f"Attempting to create tables for '{table_name}' (if they don't exist)...")
        try:
            # --- START OF ADDED DEBUG CODE ---
            print("---")
            print(f"DEBUG: The URL being used is: '{self.vec_client.service_url}'")
            print("---")
            # ---  END OF ADDED DEBUG CODE  ---

            await self.vec_client.create_tables()
            logging.info(f"Table '{table_name}' check/creation successful.")
        except Exception as e:
            logging.error(f"Failed during table creation/check for '{table_name}': {e}", exc_info=True)
            raise

    async def create_index(self) -> None:
        """Create the embedding index (e.g., DiskAnn) if it doesn't already exist."""
        index_name = f"{self.vector_settings.table_name}_embedding_idx" # Construct standard index name
        logger.info(f"Attempting to create index '{index_name}' (if it doesn't exist)...")
        try:
            # Pass the specific index type you want, e.g., DiskAnnIndex
            await self.vec_client.create_embedding_index(client.DiskAnnIndex())
            logger.info(f"Index '{index_name}' created successfully.")
        except asyncpg.exceptions.DuplicateTableError:
            # This specific error means the index already exists, which is fine.
            logger.info(f"Index '{index_name}' already exists, skipping creation.")
            # Do not re-raise this exception, allow the script to continue.
        except Exception as e:
            # Catch any other unexpected errors during index creation
            logger.error(f"An unexpected error occurred while creating index '{index_name}': {e}", exc_info=True)
            raise # Re-raise other errors to signal a real problem

    async def drop_index(self) -> None:
        """Drop the StreamingDiskANN index in the database"""
        await self.vec_client.drop_embedding_index()

    async def upsert(self, df: pd.DataFrame) -> None:
        """
        Insert or update records in the database from a pandas DataFrame.

        Args:
            df: A pandas DataFrame containing the data to insert or update.
                Expected columns: id, metadata, contents, embedding
        """
        records = df.to_records(index=False) # is this a built in function?
        await self.vec_client.upsert(list(records))
        logging.info(
            f"Inserted {len(df)} records into {self.vector_settings.table_name}"
        )

    async def search(
        self,
        query_text: str,
        limit: int = 5,
        metadata_filter: Union[dict, List[dict]] = None,
        predicates: Optional[client.Predicates] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        return_dataframe: bool = True,
    ) -> Union[List[Tuple[Any, ...]], pd.DataFrame]:
        """
        Query the vector database for similar embeddings based on input text.

        More info:
            https://github.com/timescale/docs/blob/latest/ai/python-interface-for-pgvector-and-timescale-vector.md

        Args:
            query_text: The input text to search for.
            limit: The maximum number of results to return.
            metadata_filter: A dictionary or list of dictionaries for equality-based metadata filtering.
            predicates: A Predicates object for complex metadata filtering.
                - Predicates objects are defined by the name of the metadata key, an operator, and a value.
                - Operators: ==, !=, >, >=, <, <=
                - & is used to combine multiple predicates with AND operator.
                - | is used to combine multiple predicates with OR operator.
            time_range: A tuple of (start_date, end_date) to filter results by time.
            return_dataframe: Whether to return results as a DataFrame (default: True).

        Returns:
            Either a list of tuples or a pandas DataFrame containing the search results.

        Basic Examples:
            Basic search:
                vector_store.search("What are your shipping options?")
            Search with metadata filter:
                vector_store.search("Shipping options", metadata_filter={"category": "Shipping"})
        
        Predicates Examples:
            Search with predicates:
                vector_store.search("Pricing", predicates=client.Predicates("price", ">", 100))
            Search with complex combined predicates:
                complex_pred = (client.Predicates("category", "==", "Electronics") & client.Predicates("price", "<", 1000)) | \
                               (client.Predicates("category", "==", "Books") & client.Predicates("rating", ">=", 4.5))
                vector_store.search("High-quality products", predicates=complex_pred)
        
        Time-based filtering:
            Search with time range:
                vector_store.search("Recent updates", time_range=(datetime(2024, 1, 1), datetime(2024, 1, 31)))
        """
        query_embedding = self.get_embedding(query_text)

        start_time = time.time()

        search_args = {
            "limit": limit,
        }

        if metadata_filter:
            search_args["filter"] = metadata_filter

        if predicates:
            search_args["predicates"] = predicates

        if time_range:
            start_date, end_date = time_range
            search_args["uuid_time_filter"] = client.UUIDTimeRange(start_date, end_date)

        results = await self.vec_client.search(query_embedding, **search_args)
        elapsed_time = time.time() - start_time

        logging.info(f"Vector search completed in {elapsed_time:.3f} seconds")

        if return_dataframe:
            return self._create_dataframe_from_results(results)
        else:
            return results

    def _create_dataframe_from_results(
        self,
        results: List[Tuple[Any, ...]],
    ) -> pd.DataFrame:
        """
        Create a pandas DataFrame from the search results.

        Args:
            results: A list of tuples containing the search results.

        Returns:
            A pandas DataFrame containing the formatted search results.
        """
        # Convert results to DataFrame
        df = pd.DataFrame(
            results, columns=["id", "metadata", "content", "embedding", "distance"]
        )

        # Expand metadata column
        df = pd.concat(
            [df.drop(["metadata"], axis=1), df["metadata"].apply(pd.Series)], axis=1
        )

        # Convert id to string for better readability
        df["id"] = df["id"].astype(str)
    
        return df

    async def delete(
        self,
        ids: List[str] = None,
        metadata_filter: dict = None,
        delete_all: bool = False,
    ) -> None:
        """Delete records from the vector database.

        Args:
            ids (List[str], optional): A list of record IDs to delete.
            metadata_filter (dict, optional): A dictionary of metadata key-value pairs to filter records for deletion.
            delete_all (bool, optional): A boolean flag to delete all records.

        Raises:
            ValueError: If no deletion criteria are provided or if multiple criteria are provided.

        Examples:
            Delete by IDs:
                vector_store.delete(ids=["8ab544ae-766a-11ef-81cb-decf757b836d"])

            Delete by metadata filter:
                vector_store.delete(metadata_filter={"category": "Shipping"})

            Delete all records:
                vector_store.delete(delete_all=True)
        """
        if sum(bool(x) for x in (ids, metadata_filter, delete_all)) != 1:
            raise ValueError(
                "Provide exactly one of: ids, metadata_filter, or delete_all"
            )

        if delete_all:
            await self.vec_client.delete_all()
            logging.info(f"Deleted all records from {self.vector_settings.table_name}")
        elif ids:
            await self.vec_client.delete_by_ids(ids)
            logging.info(
                f"Deleted {len(ids)} records from {self.vector_settings.table_name}"
            )
        elif metadata_filter:
            await self.vec_client.delete_by_metadata(metadata_filter)
            logging.info(
                f"Deleted records matching metadata filter from {self.vector_settings.table_name}"
            )