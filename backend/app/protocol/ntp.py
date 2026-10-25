import json, re
from dataclasses import dataclass
from app.core.schemas import ToolCall
from app.tools.registry import ToolRegistry

@dataclass
class ProtocolResult:
    plan: list[str]
    tool_calls: list[ToolCall]
    answer_seed: str

class NaturalToolProtocol:
    PLAN_RE = re.compile(r"PLAN:\s*(.*?)\n\nACTIONS:", re.DOTALL)
    ACTIONS_RE = re.compile(r"ACTIONS:\s*(.*?)\n\nANSWER:", re.DOTALL)
    ANSWER_RE = re.compile(r"ANSWER:\s*(.*)", re.DOTALL)
    ALIASES = {"search":"search_files","grep":"search_files","find":"search_files","read":"read_file","open":"read_file","list":"list_files","run":"run_command","patch":"apply_patch","edit":"apply_patch"}

    def __init__(self):
        self.registry = ToolRegistry()

    def parse_llm_output(self, text: str, user_message: str) -> ProtocolResult:
        plan_match = self.PLAN_RE.search(text)
        actions_match = self.ACTIONS_RE.search(text)
        answer_match = self.ANSWER_RE.search(text)
        plan = [line.strip("- ").strip() for line in (plan_match.group(1).splitlines() if plan_match else []) if line.strip()]
        tool_calls = []
        action_block = actions_match.group(1).strip() if actions_match else ""
        for line in action_block.splitlines():
            line = line.strip()
            if line:
                tool_calls.extend(self._normalize_action_line(line, user_message))
        if not tool_calls:
            tool_calls = self.registry.match_natural_language(user_message)
        return ProtocolResult(plan=plan, tool_calls=tool_calls, answer_seed=answer_match.group(1).strip() if answer_match else "")

    def _normalize_action_line(self, line: str, user_message: str):
        match = re.search(r"tool:([a-zA-Z0-9_\-]+)", line)
        conf = re.search(r"confidence:([0-9.]+)", line)
        args_match = re.search(r"args:(\{.*\})$", line)
        if not match:
            return []
        tool_name = self.ALIASES.get(match.group(1).strip(), match.group(1).strip())
        if not self.registry.has_tool(tool_name):
            return []
        args = {"query": user_message}
        if args_match:
            try:
                args.update(json.loads(args_match.group(1)))
            except Exception:
                pass
        return [ToolCall(tool=tool_name, arguments=args, confidence=float(conf.group(1)) if conf else 0.5, source="llm")]
