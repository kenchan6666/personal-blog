from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    mongo_uri: str = "mongodb://127.0.0.1:27019"
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
    # smtp | console — default console for local; Gmail SMTP often times out
    mail_backend: str = "console"

    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002"

    avatar_dir: str = "data/avatars"
    avatar_max_bytes: int = 2 * 1024 * 1024
