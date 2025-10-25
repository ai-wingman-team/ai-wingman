"""
Configuration management for AI Wingman.

Loads settings from environment variables with validation.
"""

from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Application environment"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Database Configuration
    postgres_user: str = Field(default="wingman", description="PostgreSQL username")
    postgres_password: str = Field(
        default="dev_password", description="PostgreSQL password"
    )
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5433, description="PostgreSQL port")
    postgres_db: str = Field(
        default="ai_wingman", description="PostgreSQL database name"
    )

    # Computed database URL
    @property
    def database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync database URL (for migrations)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Embedding Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name",
    )
    embedding_dimension: int = Field(
        default=384, description="Embedding vector dimension"
    )

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama API endpoint"
    )
    ollama_model: str = Field(default="phi3", description="Ollama model name")
    ollama_temperature: float = Field(default=0.7, description="LLM temperature")
    ollama_max_tokens: int = Field(default=500, description="Max tokens to generate")

    # Slack Configuration
    slack_bot_token: Optional[str] = Field(default=None, description="Slack bot token")
    slack_app_token: Optional[str] = Field(default=None, description="Slack app token")
    slack_workspace_id: Optional[str] = Field(
        default=None, description="Slack workspace ID"
    )

    # Application Behavior
    top_k_results: int = Field(
        default=5, description="Number of results for similarity search"
    )
    min_similarity_score: float = Field(
        default=0.7, description="Minimum similarity score for context retrieval"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Validators
    @field_validator("min_similarity_score")
    @classmethod
    def validate_similarity_score(cls, v: float) -> float:
        """Ensure similarity score is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("min_similarity_score must be between 0.0 and 1.0")
        return v

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Ensure embedding dimension is positive."""
        if v <= 0:
            raise ValueError("embedding_dimension must be positive")
        return v

    @field_validator("top_k_results")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """Ensure top_k is positive."""
        if v <= 0:
            raise ValueError("top_k_results must be positive")
        return v


# Singleton settings instance
settings = Settings()


# Helper function for debugging
def print_settings() -> None:
    """Print current settings (masks sensitive values)."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="AI Wingman Configuration")

    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    sensitive_keys = {"postgres_password", "slack_bot_token", "slack_app_token"}

    for field_name in settings.model_fields.keys():
        value = getattr(settings, field_name)
        if field_name in sensitive_keys and value:
            value = "***REDACTED***"
        table.add_row(field_name, str(value))

    console.print(table)


if __name__ == "__main__":
    # Test configuration loading
    print_settings()
