import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongodb_uri: str = Field(
        default="mongodb://aegisrca:dev-only-change-this@localhost:27017/?authSource=admin&directConnection=true",
        alias="MONGODB_URI",
    )
    mongodb_db_name: str = Field(default="aegisrca", alias="MONGODB_DB_NAME")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")
    max_tool_iterations: int = Field(default=6, alias="MAX_TOOL_ITERATIONS")
    max_tools_per_turn: int = Field(default=10, alias="MAX_TOOLS_PER_TURN")
    max_verification_attempts: int = Field(default=1, alias="MAX_VERIFICATION_ATTEMPTS")
    max_history_messages: int = Field(default=20, alias="MAX_HISTORY_MESSAGES")
    debug: bool = Field(default=True, alias="DEBUG")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ("true", "1", "t", "yes", "debug")
        return bool(v)


settings = Settings()
