from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "PDF Agent AI"
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_CONTAINER_NAME: str = "pdf-documents"

    GEMINI_API_KEY: str
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    EMAIL_ADDRESS: str = ""
    EMAIL_PASSWORD: str = ""
    SENDER_NAME: str = "Ali-PDF AI"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()