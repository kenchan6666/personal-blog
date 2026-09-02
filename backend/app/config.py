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
    # console | smtp | resend
    # resend = HTTPS to api.resend.com (works on GCP). smtp = Gmail, often
    # fails from Compute Engine IPs; OTP still prints to logs on failure.
    mail_backend: str = "console"
    resend_api_key: str = ""

    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"
    )

    avatar_dir: str = "data/avatars"
    avatar_max_bytes: int = 2 * 1024 * 1024

    # The browser never talks to Viola directly. Owner-authenticated API
    # routes proxy chat traffic to this internal service.
    agent_api_url: str = "http://127.0.0.1:8900"
    agent_internal_token: str = ""
    agent_service_token: str = ""
    agent_upload_max_bytes: int = 10 * 1024 * 1024
    uni_api_key: str = ""
    uni_api_base: str = "https://api.uniapi.io"
    agent_embedding_model: str = "gemini-embedding-001"
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "portfolio_about_me"
    public_agent_enabled: bool = True
    public_agent_model: str = "gemini-2.5-flash"
    public_agent_max_tokens: int = 350
    public_agent_rate_minute: int = 4
    public_agent_rate_hour: int = 20
    public_agent_rate_day: int = 40
    public_agent_daily_budget: int = 500

    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_callback_url: str = "http://127.0.0.1:8000/api/auth/github/callback"
    github_oauth_success_url: str = "http://localhost:3000/zh-Hant/admin"
