from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    portal_name: str = "saucedemo"
    db_path: str = "./data/app.db"
    report_email: str = "admin@example.com"

    orangehrm_url: str
    orangehrm_username: str
    orangehrm_password: str

    saucedemo_url: str
    saucedemo_password: str

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool = True
    smtp_from: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()