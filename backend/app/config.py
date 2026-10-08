from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "production"
    database_url: str
    cors_origins: str
    jwt_secret: str
    initial_admin_email: str | None = None
    initial_admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
