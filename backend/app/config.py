from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_key: str
    supabase_jwt_secret: str = ""
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    # Set to True to enforce JWT-based authentication on all protected endpoints.
    # Keep False during local development against Docker PostgreSQL.
    enforce_auth: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
