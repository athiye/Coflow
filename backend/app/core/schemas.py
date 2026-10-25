from typing import Any, Literal
from pydantic import BaseModel, Field

class IDEContext(BaseModel):
    file_path: str | None = None
    language: str | None = None
    selected_text: str | None = None
    diagnostics: list[str] = Field(default_factory=list)

class ComputerUseContext(BaseModel):
    start_url: str | None = None
    goal: str | None = None
    max_steps: int = 30
    provider: Literal["auto", "openai", "anthropic"] = "auto"
    vision_only: bool = False
    allow_destructive: bool = False
    pause_for_manual_login: bool = False
    pause_before_close: bool = False

class ChatRequest(BaseModel):
    message: str
    repo_path: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    ide_context: IDEContext | None = None
    computer_use: ComputerUseContext | None = None
    client: Literal["web", "ide", "api"] = "api"
    latency_budget_ms: int = 6000
    stream: bool = False
    action_key: str | None = None
    route_preference: Literal["auto", "cheap", "mid", "premium"] = "auto"

class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    source: str = "protocol"

class ChatResponse(BaseModel):
    route: str
    provider: str
    model: str
    plan: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    patches: list[dict[str, Any]] = Field(default_factory=list)
    answer: str
    metrics: dict[str, Any] = Field(default_factory=dict)

class ToolSummary(BaseModel):
    name: str
    description: str
    adapter: str
    aliases: list[str] = Field(default_factory=list)

class ToolListResponse(BaseModel):
    tools: list[ToolSummary]
