from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="scribe-backend")
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    database_url: str = Field(default="sqlite:///./scribe.db")
    use_demo_data: bool = Field(default=True)
    granola_api_base_url: str = Field(default="https://public-api.granola.ai/v1")
    granola_api_key: str = Field(default="demo-key")
    granola_auth_header: str = Field(default="Authorization")
    granola_auth_scheme: str = Field(default="Bearer")
    recall_region: str = Field(default="us-east-1")
    recall_api_base_url: str = Field(default="https://us-east-1.recall.ai/api/v1")
    recall_api_key: str = Field(default="")
    recall_workspace_verification_secret: str = Field(
        default="",
        validation_alias=AliasChoices("RECALL_WORKSPACE_VERIFICATION_SECRET", "RECALL_WEBHOOK_SECRET"),
    )
    recall_public_api_base_url: str = Field(default="", validation_alias="PUBLIC_API_BASE_URL")
    recall_svix_webhook_secret: str = Field(default="")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def should_use_demo_data(self) -> bool:
        return self.use_demo_data

    def missing_recall_settings(self) -> list[str]:
        required = {
            "RECALL_REGION": self.recall_region,
            "RECALL_API_KEY": self.recall_api_key,
            "RECALL_WORKSPACE_VERIFICATION_SECRET": self.recall_workspace_verification_secret,
            "PUBLIC_API_BASE_URL": self.recall_public_api_base_url,
        }
        return [name for name, value in required.items() if not value.strip()]


settings = Settings()
