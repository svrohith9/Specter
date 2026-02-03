from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMRoute(BaseModel):
    provider: str
    model: str
    priority: int = 1
    timeout: int = 15
    local: bool = False


class ExecutionConfig(BaseModel):
    max_parallel: int = 10
    timeout_seconds: int = 300
    healing_attempts: int = 3
    stream_partial: bool = True
    deterministic_planning: bool = True
    retry_attempts: int = 3
    retry_base_delay: float = 0.4
    retry_max_delay: float = 4.0
    circuit_breaker_threshold: int = 3
    circuit_breaker_timeout: int = 30


class KnowledgeConfig(BaseModel):
    graph_pruning: bool = True
    vector_cache_size: int = 10_000
    default_ttl_days: int = 30
    sensitive_ttl_days: int = 7
    summary_window: int = 20


class TelegramConfig(BaseModel):
    enabled: bool = True
    webhook_url: str | None = None


class EmailConfig(BaseModel):
    enabled: bool = False
    imap_poll_interval: int = 60


class SlackConfig(BaseModel):
    enabled: bool = False


class ChannelsConfig(BaseModel):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)


class SecurityConfig(BaseModel):
    sandbox: str = "firejail"
    allowed_imports: list[str] = Field(default_factory=list)
    blocked_patterns: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    blocked_tools: list[str] = Field(default_factory=list)
    max_execution_time: int = 30
    max_memory_mb: int = 256


class AgentConfig(BaseModel):
    db_path: str | None = None
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    role: str | None = None


class SpecterConfig(BaseModel):
    name: str = "Specter"
    autonomy_level: str = "high"
    default_agent: str = "default"
    default_user_id: str = "local"
    data_dir: str = "./data"
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    channels: ChannelsConfig = Field(default_factory=ChannelsConfig)
    llm: dict[str, list[LLMRoute]] = Field(default_factory=dict)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    agents: dict[str, AgentConfig] = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPECTER_", env_file=".env", extra="ignore")

    config_path: str = Field(default="./config.yaml", alias="CONFIG")
    specter: SpecterConfig = Field(default_factory=SpecterConfig)

    def load_yaml(self) -> None:
        import yaml

        with open(self.config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        if "specter" in raw:
            self.specter = SpecterConfig(**raw["specter"])


settings = Settings()
