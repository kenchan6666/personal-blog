from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db: str = "portfolio"
    redis_url: str = "redis://127.0.0.1:6380/0"

    owner_email: str = "ynchanhk@gmail.com"
    otp_ttl_seconds: int = 300
    otp_rate_limit: int = 5
    otp_rate_window_seconds: int = 900
    session_ttl_seconds: int = 60 * 60 * 24 * 7

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = "ynchanhk@gmail.com"
    smtp_password: str = ""
    smtp_from: str = "ynchanhk@gmail.com"

    cors_origins: str = "http://localhost:3000"
