from typing import Any
from pydantic import BaseModel, Field

class ToolManifest(BaseModel):
    name: str
    description: str
    adapter: str
    aliases: list[str] = Field(default_factory=list)
    command: list[str] | None = None
    method: str | None = None
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    input_template: dict[str, Any] = Field(default_factory=dict)
