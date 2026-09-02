from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    mongo_uri: str = ""
    mongo_db: str = "portfolio"
    redis_url: str = "redis://127.0.0.1:6380/0"
    local_data_dir: str = "data/local"

    @property
    def uses_mongo(self) -> bool:
        return bool(self.mongo_uri.strip())

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

    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
    )

    avatar_dir: str = "data/avatars"
    avatar_max_bytes: int = 2 * 1024 * 1024

    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_callback_url: str = "http://127.0.0.1:8000/api/auth/github/callback"
    github_oauth_success_url: str = "http://localhost:3000/zh-Hant/admin"
