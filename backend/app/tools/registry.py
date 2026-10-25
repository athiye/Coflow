from app.core.schemas import ToolCall, ToolSummary
from app.tools.models import ToolManifest

BUILTIN_TOOLS = {
    "list_files": ToolManifest(name="list_files", description="List repository files", adapter="builtin", aliases=["list files","repo tree"]),
    "read_file": ToolManifest(name="read_file", description="Read a file from the repository", adapter="builtin", aliases=["read file","open file"]),
    "search_files": ToolManifest(name="search_files", description="Search file names and contents", adapter="builtin", aliases=["search files","grep","find file"]),
    "apply_patch": ToolManifest(name="apply_patch", description="Apply a simple patch to a file", adapter="builtin", aliases=["apply patch","edit file"]),
    "run_command": ToolManifest(name="run_command", description="Run an approved shell command", adapter="builtin", aliases=["run command","run tests"]),
}

class ToolRegistry:
    def __init__(self):
        self._tools = dict(BUILTIN_TOOLS)

    def list_tools(self):
        return [ToolSummary(name=t.name, description=t.description, adapter=t.adapter, aliases=t.aliases) for t in self._tools.values()]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str):
        return self._tools.get(name)

    def match_natural_language(self, text: str):
        text_lower = text.lower()
        matches = []
        for tool in self._tools.values():
            best = 0.0
            for alias in tool.aliases + [tool.name]:
                if alias.lower() in text_lower:
                    best = max(best, 0.9)
            if best:
                matches.append(ToolCall(tool=tool.name, arguments={"query": text}, confidence=best, source="registry"))
        return matches[:4]
