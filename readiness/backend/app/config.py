from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # LLM Settings
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    LLM_MODEL: str = Field(default="models/gemma-4-26b-a4b-it")
    LLM_FALLBACK_MODEL: str = Field(default="models/gemma-4-31b-it")
    FIRST_TOKEN_TIMEOUT_MS: int = Field(default=2500)
    THESYS_API_KEY: Optional[str] = Field(default=None)

    # Security & Auth
    JWT_SECRET: str = Field(default="super_secret_jwt_readiness_key_production_grade_38192")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=480)
    DEMO_TECH_PASSWORD: str = Field(default="tech123")
    DEMO_SUPERVISOR_PASSWORD: str = Field(default="super123")

    # Storage
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///data/readiness.db")
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="demo_redis_secret_pass")
    
    # Optional Neo4j Mirror
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="demo_neo4j_secret_pass")
    ENABLE_NEO4J: bool = Field(default=False)

    # Server & CORS
    PORT: int = Field(default=8000)
    DASHBOARD_ORIGIN: str = Field(default="http://localhost:3000")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()
