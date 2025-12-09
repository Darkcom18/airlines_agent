"""
C1 Travel Agent System - Configuration Settings
Uses pydantic-settings for environment variable management
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SFTechCredentials(BaseSettings):
    """SFTech API Credentials for a specific source."""
    token: str = ""
    password: str = ""
    account: str = ""


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # LLM Configuration
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        alias="DEEPSEEK_BASE_URL"
    )

    # SFTech API Base URL
    sftech_api_base: str = Field(
        default="https://api-product.sftech.vn",
        alias="SFTECH_API_BASE"
    )

    # SFTech F1 Credentials
    f1_api_token: str = Field(default="", alias="F1_API_TOKEN")
    f1_api_password: str = Field(default="", alias="F1_API_PASSWORD")
    f1_api_account: str = Field(default="", alias="F1_API_ACCOUNT")

    # SFTech F10 Credentials
    f10_api_token: str = Field(default="", alias="F10_API_TOKEN")
    f10_api_password: str = Field(default="", alias="F10_API_PASSWORD")
    f10_api_account: str = Field(default="", alias="F10_API_ACCOUNT")

    # SFTech VJ Credentials
    vj_api_token: str = Field(default="", alias="VJ_API_TOKEN")
    vj_api_password: str = Field(default="", alias="VJ_API_PASSWORD")
    vj_api_account: str = Field(default="", alias="VJ_API_ACCOUNT")

    # Database
    postgres_password: str = Field(default="c1password", alias="POSTGRES_PASSWORD")
    database_url: str = Field(
        default="postgresql+asyncpg://c1user:c1password@localhost:5432/c1_travel",
        alias="DATABASE_URL"
    )

    # Services
    mcp_server_url: str = Field(default="http://localhost:8001", alias="MCP_SERVER_URL")
    api_url: str = Field(default="http://localhost:8000", alias="API_URL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # JWT
    jwt_secret_key: str = Field(
        default="c1-secret-key-change-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=30, alias="JWT_EXPIRE_MINUTES")

    def get_sftech_headers(self, source: str = "F1") -> dict:
        """Get SFTech API headers for a specific source."""
        source = source.upper()

        if source == "F1":
            return {
                "api-token": self.f1_api_token,
                "api-password": self.f1_api_password,
                "api-account": self.f1_api_account,
                "Content-Type": "application/json"
            }
        elif source == "F10":
            return {
                "api-token": self.f10_api_token,
                "api-password": self.f10_api_password,
                "api-account": self.f10_api_account,
                "Content-Type": "application/json"
            }
        elif source == "VJ":
            return {
                "api-token": self.vj_api_token,
                "api-password": self.vj_api_password,
                "api-account": self.vj_api_account,
                "Content-Type": "application/json"
            }
        else:
            raise ValueError(f"Unknown source: {source}. Use F1, F10, or VJ")

    @property
    def sftech_flight_search_url(self) -> str:
        """Get the flight search endpoint URL."""
        return f"{self.sftech_api_base}/api/v1/flights/search"

    @property
    def sftech_flight_details_url(self) -> str:
        """Get the flight details endpoint URL."""
        return f"{self.sftech_api_base}/api/v1/flights/details"

    @property
    def sftech_booking_url(self) -> str:
        """Get the booking endpoint URL."""
        return f"{self.sftech_api_base}/api/v1/flights/booking"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
