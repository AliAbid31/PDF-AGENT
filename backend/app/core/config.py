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
    RESEND_API_KEY: str
    EMAIL_FROM: str = "onboarding@resend.dev"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()