import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime
import uuid

from app.database import vector_store


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
    mocker.patch('app.database.vector_store.OpenAI', return_value=mock_openai_client)
    mocker.patch('timescale_vector.client.Sync', return_value=mock_vec_client)

    store = VectorStore()
    store.mock_settings = mock_settings
    store.mock_openai_client = mock_openai_client
    store.mock_vec_client = mock_vec_client
    return store

def test_vector_store_initialization(vector_store_instance, mock_settings, mock_openai_client, mock_vec_client):
    """Test if VectorStore initializes correctly with mocked dependencies."""
    store = vector_store_instance # Get the instance from the fixture


    assert store.settings == mock_settings
    assert store.openai_client == mock_openai_client
    assert store.vec_client == mock_vec_client
    assert store.embedding_model == mock_settings.openai.embedding_model


    vector_store_instance.mock_openai_client.assert_called_once_with(api_key=mock_settings.openai.api_key) # Correction: OpenAI() itself is mocked, so check the class call
    assert store.vec_client == mock_vec_client