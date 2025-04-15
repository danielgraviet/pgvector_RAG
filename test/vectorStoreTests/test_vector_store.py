import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime
import uuid

from app.database.vector_store import VectorStore

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.openai.api_key = "fake_api_key"
    settings.openai.embedding_model = "text-embedding-ada-002"
    settings.vector_store.table_name = "test_embeddings"
    settings.vector_store.embedding_dimensions = 1536
    settings.vector_store.time_partition_interval = pd.Timedelta(days=7)
    settings.database.service_url = "postgresql://user:pass@fakehost:5432/fakedb"
    return settings

@pytest.fixture
def mock_openai_client(mocker):
    mock_client = MagicMock()
    mock_embedding_response = MagicMock()
    mock_embedding_data = MagicMock()
    mock_embedding_data.embedding = [0.1] * 1536
    mock_embedding_response.data = [mock_embedding_data]
    mock_client.embeddings.create.return_value = mock_embedding_response
    return mock_client

@pytest.fixture
def mock_vec_client(mocker):
    mock_instance = MagicMock()
    mock_instance.search.return_value = [
        (uuid.uuid4(), {"category": "Test"}, "Test content 1", [0.1] * 1536, 0.1),
        (uuid.uuid4(), {"category": "Test"}, "Test content 2", [0.2] * 1536, 0.2),
    ]
    return mock_instance

@pytest.fixture
def vector_store_instance(mocker, mock_settings, mock_openai_client, mock_vec_client):
    mocker.patch('app.database.vector_store.get_settings', return_value=mock_settings)
    mock_openai_class = mocker.patch('app.database.vector_store.OpenAI', return_value=mock_openai_client)
    mock_timescale_sync_class = mocker.patch('timescale_vector.client.Sync', return_value=mock_vec_client) 

    store = VectorStore()

    store.mock_openai_class = mock_openai_class
    store.mock_timescale_sync_class = mock_timescale_sync_class
    store.mock_openai_client = mock_openai_client 
    store.mock_vec_client = mock_vec_client       
    store.mock_settings = mock_settings           

    return store

def test_vector_store_initialization(vector_store_instance, mock_settings):
    """Test if VectorStore initializes correctly with mocked dependencies."""
    print("\nRunning Test: test_vector_store_initialization")
    store = vector_store_instance

    # Assert attributes are set correctly using the mocks
    assert store.settings == mock_settings                 # Check settings object
    assert store.openai_client == store.mock_openai_client # Check the returned OpenAI instance
    assert store.vec_client == store.mock_vec_client       # Check the returned Sync instance
    assert store.embedding_model == mock_settings.openai.embedding_model

    # Assert the mocked OpenAI *class* was called correctly
    store.mock_openai_class.assert_called_once_with(api_key=mock_settings.openai.api_key)

    store.mock_timescale_sync_class.assert_called_once_with(
        mock_settings.database.service_url,
        mock_settings.vector_store.table_name,
        mock_settings.vector_store.embedding_dimensions,
        time_partition_interval=mock_settings.vector_store.time_partition_interval,
    )
    
def test_get_embedding(vector_store_instance):
    print("\nRunning Test: valid_test_get_embedding")
    # initialize the vector store using the passed in instance
    store = vector_store_instance
    
    # call the method "get_embedding" and store the result
    embeddingList = store.get_embedding("testString")
    
    # make sure it returns something 
    assert len(embeddingList) != 0
    
def test_get_embedding_empty_input(vector_store_instance):
    print("\nRunning Test: test_get_embedding_empty_input")
    # initialize the vector store using the passed in instance
    store = vector_store_instance
    
    # call the method "get_embedding" with empty string. 
    try:
        embeddingList = store.get_embedding("")
        assert False, "Expected ValueError for empty input, but none was raised"
    except ValueError as e:
        print(f"\nValueError caught: {e}") 
    
    
    