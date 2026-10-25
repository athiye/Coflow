from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core app config
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # Providers
    cheap_provider: str = Field(default="mock", alias="CHEAP_PROVIDER")
    mid_provider: str = Field(default="openai_responses", alias="MID_PROVIDER")
    premium_provider: str = Field(default="openai_responses", alias="PREMIUM_PROVIDER")

    # Models
    cheap_model: str = Field(default="gpt-4.1-mini", alias="CHEAP_MODEL")
    mid_model: str = Field(default="gpt-4.1", alias="MID_MODEL")
    premium_model: str = Field(default="gpt-5", alias="PREMIUM_MODEL")

    # API keys
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Tool execution
    enable_tool_execution: bool = Field(default=True, alias="ENABLE_TOOL_EXECUTION")
    max_tool_steps: int = Field(default=8, alias="MAX_TOOL_STEPS")
    max_repo_files: int = Field(default=300, alias="MAX_REPO_FILES")
    max_file_bytes: int = Field(default=250000, alias="MAX_FILE_BYTES")
    command_timeout_seconds: int = Field(default=30, alias="COMMAND_TIMEOUT_SECONDS")
    allow_shell_commands: bool = Field(default=True, alias="ALLOW_SHELL_COMMANDS")
    allowed_command_prefixes: str = Field(
        default="python,python3,pytest,git,npm,pnpm,yarn,node,ruff,black,mypy,uv",
        alias="ALLOWED_COMMAND_PREFIXES"
    )

    # Computer use
    computer_use_enabled: bool = Field(default=True, alias="COMPUTER_USE_ENABLED")
    computer_use_headless: bool = Field(default=True, alias="COMPUTER_USE_HEADLESS")
    computer_use_max_steps: int = Field(default=6, alias="COMPUTER_USE_MAX_STEPS")
    computer_use_screenshot_dir: str = Field(default="./computer_use_artifacts", alias="COMPUTER_USE_SCREENSHOT_DIR")
    computer_use_step_delay_ms: int = Field(default=2500, alias="COMPUTER_USE_STEP_DELAY_MS")

    @property
    def allowed_command_prefix_list(self) -> list[str]:
        return [x.strip() for x in self.allowed_command_prefixes.split(",") if x.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
