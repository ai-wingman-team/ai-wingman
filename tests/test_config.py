"""
Test configuration management.
"""

import pytest
from ai_wingman.config import settings, Settings


def test_settings_load():
    """Test that settings load correctly."""
    assert settings is not None
    assert isinstance(settings, Settings)


def test_database_url_format():
    """Test database URL is correctly formatted."""
    url = settings.database_url
    assert url.startswith("postgresql+asyncpg://")
    assert settings.postgres_user in url
    assert settings.postgres_host in url
    assert str(settings.postgres_port) in url
    assert settings.postgres_db in url


def test_database_url_sync_format():
    """Test sync database URL is correctly formatted."""
    url = settings.database_url_sync
    assert url.startswith("postgresql://")
    assert "asyncpg" not in url


def test_embedding_dimension_validation():
    """Test embedding dimension is positive."""
    assert settings.embedding_dimension > 0
    assert settings.embedding_dimension == 384


def test_similarity_threshold_validation():
    """Test similarity threshold is in valid range."""
    assert 0.0 <= settings.min_similarity_score <= 1.0


def test_top_k_results_validation():
    """Test top_k_results is positive."""
    assert settings.top_k_results > 0


def test_app_env_values():
    """Test app_env has valid value."""
    valid_envs = ["development", "staging", "production"]
    assert settings.app_env in valid_envs


def test_ollama_configuration():
    """Test Ollama configuration."""
    assert settings.ollama_base_url.startswith("http")
    assert settings.ollama_model
    assert 0.0 <= settings.ollama_temperature <= 2.0
    assert settings.ollama_max_tokens > 0
