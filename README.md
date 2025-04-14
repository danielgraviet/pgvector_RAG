# AI-Powered FAQ System with Timescale Vector and OpenAI for Gunter Injury Law

## Overview
I wanted to create this project after hearing about Retrieval-Augmented Generation (RAG) systems
and decided to apply it to my work at Gunter Injury Law. It uses OpenAI's language models for making
embeddings, synthesizing answers, and also uses Timescale Vector for effecient storage and search of 
text embeddings. 

I designed it to take a single question at a time, find relevant information fomr a knowledge base stored in Timescale
DB, and then it uses GPT-4o to generate a coherent and contextually relevant answer based ONLY on the retrieved information.
This way, it reduces the chance of AI hallucinations for more accurate answers regarding the law firm. 

## Example
<img src="./example.png" alt="Example Image" width="300" height="200">

## Features

*   **Vector Embeddings:** Generates text embeddings using OpenAI models (`text-embedding-3-small` by default).
*   **Vector Storage:** Uses Timescale Vector for storing text content, metadata, and embeddings.
*   **Efficient Search:** Performs fast similarity searches using Timescale Vector's capabilities (including DiskANN index support).
*   **Flexible Filtering:** Supports searching with:
    *   Metadata equality filters.
    *   Complex metadata predicates (`>`, `<`, `>=`, `<=`, `!=`, `==`, `&`, `|`).
    *   Time range filtering based on record creation time (UUIDv1).
*   **LLM Integration:** Uses OpenAI (GPT-4o by default) via the `instructor` library to synthesize answers based on retrieved context, ensuring structured output.
*   **Configurable:** Settings managed via `.env` file and Pydantic models for easy configuration (API keys, model names, database connection, etc.).
*   **Data Ingestion Script:** Includes a script (`insert_vectors.py`) to process a CSV file, generate embeddings, and populate the vector database.
*   **Example Usage:** Demonstrates querying and answer synthesis with a sample script (`law_faq.py`).
*   **Colored Output:** Provides visually distinct console output for better readability during interaction (`colors.py`).
*   **Dockerized Database:** Includes a `docker-compose.yml` file for easy setup of a local TimescaleDB instance.


## Core Components

*   **`settings.py`**: Defines and manages application settings using Pydantic, loading sensitive information (like API keys and database URLs) from a `.env` file. It configures OpenAI, Database, and Vector Store parameters.
*   **`vector_store.py` (`VectorStore` class)**: Handles all interactions with the Timescale Vector database. This includes:
    *   Connecting to the database.
    *   Creating tables and indexes (DiskANN).
    *   Generating embeddings via OpenAI API.
    *   Upserting data (inserting or updating records).
    *   Performing vector similarity searches with various filtering options.
    *   Deleting records.
*   **`llm_factory.py` (`LLMFactory` class)**: A factory class to initialize and provide access to configured LLM clients (currently supports OpenAI, extensible to others like Anthropic, Llama). Uses `instructor` for reliable structured output.
*   **`synthesizer.py` (`Synthesizer` class)**: Takes a user question and retrieved context (as a DataFrame) and uses the `LLMFactory` to prompt an AI model. It generates a structured response containing the synthesized answer, the AI's thought process, and a flag indicating if the context was sufficient.
*   **`insert_vectors.py`**: A script to load data from a specified CSV file (e.g., `law_faq_dataset.csv`), process each row (creating content strings, generating embeddings, adding metadata with timestamps), and insert the data into the Timescale Vector database using the `VectorStore` class.
*   **`law_faq.py`**: An example script demonstrating the end-to-end process: defining a question, searching the `VectorStore` for relevant context, passing the question and context to the `Synthesizer`, and printing the formatted response using `colors.py`.
*   **`colors.py`**: A utility module defining color constants using `colorama` for enhancing terminal output readability.
*   **`docker-compose.yml`**: Defines a Docker service for running a TimescaleDB instance locally, pre-configured for use with the application.
*   **`.env` (Required, not provided)**: Stores sensitive configuration like API keys and database connection strings.

## Prerequisites

*   Python 3.8+
*   Docker and Docker Compose
*   Git (for cloning the repository)
*   OpenAI API Key

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-name>
    ```

2.  **Set up Python Environment:**
    It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `.\venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    Create a `requirements.txt` file with the necessary libraries:
    ```txt
    # requirements.txt
    pydantic
    python-dotenv
    openai
    timescale_vector
    pandas
    colorama
    instructor
    # Add anthropic if you plan to use it via LLMFactory
    # anthropic
    ```
    Then install them:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory and add your configuration:
    ```dotenv
    # .env

    # Your OpenAI API Key
    OPENAI_API_KEY="sk-..."

    # Service URL for TimescaleDB. This default works with the docker-compose.yml
    TIMESCALE_SERVICE_URL="postgresql://postgres:password@localhost:5432/postgres"

    # Optional: Override default models or other settings if needed
    # OPENAI_DEFAULT_MODEL="gpt-4o"
    # OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
    ```
    Replace `"sk-..."` with your actual OpenAI API key.

5.  **Start the Database:**
    Run the TimescaleDB container using Docker Compose:
    ```bash
    docker-compose up -d
    ```
    This will start a TimescaleDB instance accessible at `localhost:5432`.

## Usage

1.  **Prepare Data:**
    *   Ensure you have your FAQ data in a CSV file (e.g., `law_faq_dataset.csv` as used in `insert_vectors.py`). The script expects columns like `question`, `answer`, and `category`.
    *   Place the CSV file in a location accessible by the script (e.g., a `data/` directory). You might need to adjust the path in `insert_vectors.py`:
        ```python
        # In insert_vectors.py, adjust this line if needed:
        df = pd.read_csv("../data/law_faq_dataset.csv", sep=";")
        # Or perhaps:
        # df = pd.read_csv("./data/law_faq_dataset.csv", sep=";")
        ```
    *   Make sure the `data` directory exists if you use a path like `./data/`.

2.  **Ingest Data into Timescale Vector:**
    Run the `insert_vectors.py` script. This will:
    *   Read the CSV data.
    *   Generate embeddings for each question-answer pair using OpenAI.
    *   Create the necessary table (`embeddings` by default) and a DiskANN index in TimescaleDB.
    *   Insert the data into the table.
    ```bash
    # Assuming insert_vectors.py is in the root or a scripts/ directory
    python insert_vectors.py
    # or python scripts/insert_vectors.py
    ```
    *(Adjust the command based on your project structure)*

3.  **Run Example Queries:**
    Execute the `law_faq.py` script to see the system in action. It performs a similarity search for predefined questions, synthesizes an answer using the retrieved context, and prints the formatted output.
    ```bash
    # Assuming law_faq.py is in the root or an examples/ directory
    python law_faq.py
    # or python examples/law_faq.py
    ```
    *(Adjust the command based on your project structure)*

## Configuration

Application settings are managed in `config/settings.py` using Pydantic models and loaded from the `.env` file.

**Key Environment Variables:**

*   `OPENAI_API_KEY`: **Required**. Your secret API key for OpenAI.
*   `TIMESCALE_SERVICE_URL`: **Required**. The connection string for your TimescaleDB instance. The default `postgresql://postgres:password@localhost:5432/postgres` works with the provided `docker-compose.yml`.

**Other Configurable Settings (via `settings.py` or potentially `.env` overrides if implemented):**

*   `OPENAI_DEFAULT_MODEL`: The default OpenAI chat model (e.g., "gpt-4o").
*   `OPENAI_EMBEDDING_MODEL`: The OpenAI model used for generating embeddings (e.g., "text-embedding-3-small").
*   `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_MAX_RETRIES`: Parameters for LLM generation.
*   `VECTOR_STORE_TABLE_NAME`: Name of the table used in TimescaleDB.
*   `VECTOR_STORE_EMBEDDING_DIMENSIONS`: Dimensions of the embeddings (must match the embedding model used, e.g., 1536 for `text-embedding-3-small`).
*   `VECTOR_STORE_TIME_PARTITION_INTERVAL`: Time interval for partitioning data in TimescaleDB.

## Notes

*   The `insert_vectors.py` script uses `uuid_from_time(datetime.now())` to generate time-based UUIDs (UUIDv1) for records. This allows for time-based filtering in searches. If your data has specific timestamps, you can modify the script to use those timestamps when generating UUIDs.
*   Ensure your OpenAI API key has sufficient credits/quota for generating embeddings and completions.
*   The `vector_store.py` search method provides powerful filtering capabilities. Refer to its docstrings and the Timescale Vector documentation for more advanced usage.

## Potential Improvements / Future Work

*   Implement error handling more robustly.
*   Add unit and integration tests.
*   Support other vector databases or LLM providers more explicitly.
*   Develop a user interface (CLI or Web).
*   Add caching for embeddings to reduce API calls.
*   Optimize batch processing for data ingestion.
