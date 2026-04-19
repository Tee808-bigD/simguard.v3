from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # Nokia Network as Code
    nac_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Database
    database_url: str = "sqlite:///./simguard.db"

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Rate limiting
    rate_limit_per_minute: int = 60
    auth_rate_limit_per_minute: int = 10

    # Nokia OAuth endpoints
    nac_auth_clientcredentials_url: str = "https://nac-authorization-server.p-eu.rapidapi.com"
    nac_auth_clientcredentials_host: str = "nac-authorization-server.nokia.rapidapi.com"
    nac_wellknown_metadata_url: str = "https://well-known-metadata.p-eu.rapidapi.com"
    nac_wellknown_metadata_host: str = "well-known-metadata.nokia.rapidapi.com"
    nac_number_verification_url: str = "https://number-verification.p-eu.rapidapi.com"
    nac_number_verification_host: str = "number-verification.nokia.rapidapi.com"

    # Payload limits
    max_payload_size: int = 1_048_576  # 1 MB

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
