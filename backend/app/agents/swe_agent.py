from __future__ import annotations
import json, os, re, ntpath
from time import perf_counter
from typing import Any, AsyncIterator
from app.core.prompt_library import get_action_prompt
from app.core.router import ModelRouter
from app.core.schemas import ChatRequest, ChatResponse, ToolCall
from app.protocol.ntp import NaturalToolProtocol
from app.providers.factory import ProviderFactory
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

BASE_SYSTEM_PROMPT = """
You are an autonomous software engineering agent.
Be decisive, practical, and minimal.

You may only use these tools:
- list_files
- read_file
- search_files
- apply_patch
- run_command

Rules:
- For repo-wide architecture, onboarding, refactor, release, product, and brownfield prompts, use list_files first.
- For a specific file, use read_file first only when the path is known.
- If only a filename is known and the repo root is broad, search for the filename first.
- Never invent tool names.
- Return exactly this format:

PLAN:
1. concise step

ACTIONS:
tool:<name> confidence:<0-1> args:{\"optional\":\"json\"}

ANSWER:
concise engineering answer
""".strip()

REPO_WIDE_ACTIONS = {
    "explain_architecture",
    "onboarding_explainer",
    "refactor_plan",
    "pm_repo_analysis",
    "brownfield_impact",
    "release_readiness",
    "incident_prevention",
    "reverse_prd",
}

class SWEAgent:
    def __init__(self):
        self.router = ModelRouter()
        self.protocol = NaturalToolProtocol()
        self.executor = ToolExecutor()
        self.registry = ToolRegistry()

    async def handle(self, request: ChatRequest) -> ChatResponse:
        start = perf_counter()
        decision = self.router.route(request)
        provider = ProviderFactory.get(decision.provider)
        system_prompt = self._build_system_prompt(request)

        llm_output = await provider.complete(
            system_prompt,
            self._build_prompt(request),
            decision.model,
            {"tier": decision.tier},
        )
        protocol_result = self.protocol.parse_llm_output(llm_output, request.message)
        tool_calls = self._enrich_tool_calls(protocol_result.tool_calls, request)
        tool_results, patches = await self._execute_tool_calls(tool_calls, request.repo_path)
        tool_results, patches = await self._maybe_expand_search_reads(request, tool_results, patches)
        tool_results = await self._maybe_expand_repo_reads(request, tool_results)
        answer = await self._synthesize_final_answer(
            provider,
            decision.model,
            request,
            protocol_result.answer_seed,
            tool_results,
            decision.reason,
        )
        elapsed_ms = round((perf_counter() - start) * 1000, 2)

        return ChatResponse(
            route=decision.tier,
            provider=provider.name,
            model=decision.model,
            plan=protocol_result.plan or self._default_plan(request),
            tool_calls=tool_calls,
            tool_results=tool_results,
            patches=patches,
            answer=answer,
            metrics={
                "latency_ms": elapsed_ms,
                "tool_count": len(tool_calls),
                "patch_count": len(patches),
                "action_key": request.action_key,
            },
        )

    async def stream_handle(self, request: ChatRequest) -> AsyncIterator[dict[str, Any]]:
        result = await self.handle(request)
        yield {"type": "route", "data": {"route": result.route, "provider": result.provider, "model": result.model}}
        yield {"type": "plan", "data": result.plan}
        yield {"type": "tool_calls", "data": [x.model_dump() for x in result.tool_calls]}
        if result.patches:
            yield {"type": "patches", "data": result.patches}
        yield {"type": "final", "data": result.model_dump()}

    def _is_reverse_prd_like(self, request: ChatRequest) -> bool:
        text = request.message.lower()
        return (
            request.action_key == "reverse_prd"
            or "reverse prd" in text
            or ("prd" in text and "repo" in text)
            or ("product vision" in text and "user journeys" in text and "roadmap" in text)
            or ("target users" in text and "jobs to be done" in text and "implemented features" in text)
        )

    def _is_repo_wide_like(self, request: ChatRequest) -> bool:
        return request.action_key in REPO_WIDE_ACTIONS or self._is_reverse_prd_like(request)

    def _build_system_prompt(self, request: ChatRequest) -> str:
        action = get_action_prompt(request.action_key)
        if action:
            return BASE_SYSTEM_PROMPT + "\n\nAdditional action guidance:\n" + action.system_instructions
        if self._is_reverse_prd_like(request):
            return BASE_SYSTEM_PROMPT + "\n\nAdditional action guidance:\nFor reverse PRD generation, first list repository files, then read likely product-defining and runtime files such as README.md, MVP specs, requirements, package manifests, backend entry points, frontend entry points, templates/pages, API handlers, and key domain modules. Synthesize a product-facing PRD grounded in the code. Clearly distinguish confirmed implemented behavior, inferred product intent, missing but implied capabilities, and technical constraints visible from the implementation."
        return BASE_SYSTEM_PROMPT

    def _build_prompt(self, request: ChatRequest) -> str:
        parts = [f"User request: {request.message}"]
        if request.repo_path:
            parts.append(f"Repository path: {request.repo_path}")
        if request.ide_context:
            parts.append(f"IDE file: {request.ide_context.file_path}")
            parts.append(f"Language: {request.ide_context.language}")
            if request.ide_context.selected_text:
                parts.append(f"Selected code:\n{request.ide_context.selected_text[:4000]}")
        return "\n\n".join(parts)

    def _default_plan(self, request: ChatRequest) -> list[str]:
        if self._is_repo_wide_like(request):
            return [
                "List core runtime and product-defining files in the repository.",
                "Read likely entry points, product-facing files, and business-logic modules.",
                "Synthesize a structured answer grounded in the codebase.",
            ]
        return [
            "Analyze the request and identify the smallest effective action.",
            "Inspect the relevant repository context before changing anything.",
            "Execute bounded tools or reads, then summarize results clearly.",
        ]

    def _extract_path_or_filename_from_message(self, text: str) -> str | None:
        abs_match = re.search(r'([A-Za-z]:\\[^\s"\']+|[A-Za-z]:\\[^"\']+)', text)
        if abs_match:
            return abs_match.group(1).strip()
        file_match = re.search(r'([A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)', text)
        return file_match.group(1).strip() if file_match else None

    def _is_probably_absolute_windows_path(self, value: str) -> bool:
        return bool(re.match(r'^[A-Za-z]:\\', value))

    def _to_repo_relative_path(self, maybe_abs_path: str, repo_path: str | None) -> str | None:
        if not repo_path:
            return maybe_abs_path
        try:
            abs_repo = os.path.abspath(repo_path)
            abs_target = os.path.abspath(maybe_abs_path)
            if os.path.commonpath([abs_repo, abs_target]) == abs_repo:
                return os.path.relpath(abs_target, abs_repo)
            return None
        except Exception:
            return None

    def _basename_only(self, value: str) -> str:
        return ntpath.basename(value.replace("/", "\\"))

    def _enrich_tool_calls(self, tool_calls: list[ToolCall], request: ChatRequest) -> list[ToolCall]:
        raw_message = request.message
        message = raw_message.lower()
        inferred = self._extract_path_or_filename_from_message(raw_message)
        ide_file_path = None if request.client == "web" else (
            request.ide_context.file_path if request.ide_context and request.ide_context.file_path else None
        )
        if not inferred and ide_file_path:
            inferred = ide_file_path

        repo_relative = None
        basename = None
        if inferred:
            if self._is_probably_absolute_windows_path(inferred):
                repo_relative = self._to_repo_relative_path(inferred, request.repo_path)
                basename = self._basename_only(inferred)
            else:
                basename = self._basename_only(inferred)
                if any(sep in inferred for sep in ["/", "\\"]):
                    repo_relative = inferred

        enriched: list[ToolCall] = []
        seen: set[str] = set()

        for call in tool_calls:
            key = json.dumps(call.model_dump(), sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            args = dict(call.arguments)
            tool_name = call.tool

            if self._is_repo_wide_like(request) and tool_name == "read_file" and not repo_relative:
                tool_name = "list_files"
                args = {"pattern": "*"}

            if tool_name == "list_files":
                args.pop("directory", None)
                args.pop("path", None)
                if "pattern" not in args:
                    args["pattern"] = "*"

            if tool_name == "read_file":
                if repo_relative:
                    args["path"] = repo_relative
                elif basename:
                    tool_name = "search_files"
                    args = {"query": basename}
            elif tool_name in {"list_files", "search_files"} and basename and any(
                w in message for w in ["summarize", "summary", "explain", "analyze", "inspect", "debug", "review"]
            ):
                tool_name = "search_files"
                args = {"query": basename}

            enriched.append(
                ToolCall(
                    tool=tool_name,
                    arguments=args,
                    confidence=call.confidence,
                    source=call.source,
                )
            )

        if not enriched:
            if self._is_repo_wide_like(request):
                enriched.append(
                    ToolCall(tool="list_files", arguments={"pattern": "*"}, confidence=0.95, source="fallback")
                )
            elif repo_relative:
                enriched.append(
                    ToolCall(tool="read_file", arguments={"path": repo_relative}, confidence=0.95, source="fallback")
                )
            elif basename:
                enriched.append(
                    ToolCall(tool="search_files", arguments={"query": basename}, confidence=0.95, source="fallback")
                )

        return enriched

    async def _execute_tool_calls(self, tool_calls: list[ToolCall], repo_path: str | None):
        tool_results: list[dict[str, Any]] = []
        patches: list[dict[str, Any]] = []
        for tool_call in tool_calls[:8]:
            manifest = self.registry.get(tool_call.tool)
            if not manifest:
                continue
            result = await self.executor.execute(manifest, repo_path, tool_call.arguments)
            tool_results.append(result)
            if result.get("diff"):
                patches.append({"tool": tool_call.tool, "path": result.get("path"), "diff": result["diff"]})
        return tool_results, patches

    async def _maybe_expand_search_reads(
        self,
        request: ChatRequest,
        tool_results: list[dict[str, Any]],
        patches: list[dict[str, Any]],
    ):
        search_result = next((r for r in tool_results if r.get("tool") == "search_files" and r.get("results")), None)
        if not search_result:
            return tool_results, patches

        paths: list[str] = []
        seen: set[str] = set()
        for item in search_result["results"]:
            path = item.get("path")
            if path and path not in seen:
                seen.add(path)
                paths.append(path)

        if len(paths) == 1:
            manifest = self.registry.get("read_file")
            if manifest:
                tool_results.append(await self.executor.execute(manifest, request.repo_path, {"path": paths[0]}))

        return tool_results, patches

    def _pick_repo_files(self, request: ChatRequest, file_list: list[str]) -> list[str]:
        file_set = set(file_list)

        reverse_prd_priority = [
            "README.md",
            "MVP_SPEC.md",
            "requirements.txt",
            "package.json",
            "pyproject.toml",
            "server.js",
            "app.js",
            "index.js",
            "main.py",
            "app.py",
            "public/index.html",
            "public/app.js",
            "templates/index.html",
            "templates/prospects.html",
            "templates/drafts.html",
            "templates/settings.html",
            "templates/followups.html",
            "templates/base.html",
        ]

        general_priority = [
            "README.md",
            "package.json",
            "server.js",
            "app.js",
            "index.js",
            "main.py",
            "app.py",
            "public/index.html",
            "public/app.js",
            "src/index.ts",
            "src/index.js",
        ]

        priority = reverse_prd_priority if self._is_reverse_prd_like(request) or request.action_key == "pm_repo_analysis" else general_priority
        selected = [x for x in priority if x in file_set]

        if not selected:
            for path in file_list:
                lower = path.lower()
                if lower.endswith((".js", ".ts", ".py", ".md", ".json", ".html", ".css", ".yaml", ".yml", ".toml")):
                    selected.append(path)
                if len(selected) >= 8:
                    break

        return selected[:8]

    async def _maybe_expand_repo_reads(self, request: ChatRequest, tool_results: list[dict[str, Any]]):
        if not self._is_repo_wide_like(request):
            return tool_results

        list_result = next((r for r in tool_results if r.get("tool") == "list_files" and r.get("files")), None)
        if not list_result:
            return tool_results

        candidate_files = self._pick_repo_files(request, list_result["files"])
        manifest = self.registry.get("read_file")
        if not manifest:
            return tool_results

        already = {r.get("path") for r in tool_results if r.get("tool") == "read_file"}
        for rel_path in candidate_files:
            if rel_path in already:
                continue
            tool_results.append(await self.executor.execute(manifest, request.repo_path, {"path": rel_path}))

        return tool_results

    async def _synthesize_final_answer(
        self,
        provider,
        model: str,
        request: ChatRequest,
        initial_answer_seed: str,
        tool_results: list[dict[str, Any]],
        router_reason: str,
    ) -> str:
        file_contents: list[str] = []
        for result in tool_results:
            if result.get("tool") == "read_file" and result.get("content"):
                file_contents.append(f"FILE: {result.get('path','<unknown>')}\n{result['content'][:3500]}")

        if file_contents:
            if self._is_reverse_prd_like(request):
                synthesis_prompt = f"""
User request:
{request.message}

Repository path:
{request.repo_path}

Generate a reverse PRD grounded in the repository evidence below.

Required structure:
1. Product overview
2. Target users / personas
3. Jobs to be done
4. Key user journeys
5. Confirmed implemented features
6. Inferred product intent
7. Non-functional requirements and technical constraints
8. Gaps, risks, and limitations
9. Suggested roadmap
10. Open questions / assumptions

Rules:
- Clearly separate confirmed functionality from inferred functionality.
- Ground conclusions in code and docs.
- Do not talk about tool execution.
- If the code reveals implementation constraints, surface them explicitly.

Evidence:
{chr(10).join(file_contents)}
""".strip()
            else:
                synthesis_prompt = f"""
User request:
{request.message}

Repository path:
{request.repo_path}

Use the following repository evidence to answer directly. Do not describe tool execution.
If the request asks for a plan, produce a concrete phased plan.
If the request asks for architecture, explain entry points, main modules, and execution flow.
If the request asks for product or SDLC value, connect code structure to product and release implications.

Evidence:
{chr(10).join(file_contents)}
""".strip()

            try:
                return await provider.complete(
                    "You are a precise software engineering and SDLC assistant.",
                    synthesis_prompt,
                    model,
                    {"phase": "synthesis"},
                )
            except Exception as exc:
                return self._compose_answer(
                    request,
                    f"{router_reason} (synthesis failed: {exc})",
                    initial_answer_seed,
                    tool_results,
                )

        return self._compose_answer(request, router_reason, initial_answer_seed, tool_results)

    def _compose_answer(self, request: ChatRequest, reason: str, answer_seed: str, tool_results: list[dict[str, Any]]) -> str:
        lines = [f"Router rationale: {reason}."]
        if answer_seed and not self._is_repo_wide_like(request):
            lines.append(answer_seed)
        if tool_results:
            lines.append("Tool execution summary:")

        for item in tool_results:
            status = "ok" if item.get("ok") else "failed"
            summary = f"- {item.get('tool')}: {status}"
            if item.get("path"):
                summary += f" ({item.get('path')})"
            lines.append(summary)

            if item.get("files"):
                lines.append("Files found:")
                for f in item["files"][:50]:
                    lines.append(f"- {f}")
                if len(item["files"]) > 50:
                    lines.append(f"... and {len(item['files']) - 50} more files")
            elif item.get("results"):
                lines.append(json.dumps(item["results"][:10], indent=2))
            elif item.get("content"):
                lines.append(f"Read file content from {item.get('path','<unknown>')}.")
            elif item.get("stdout"):
                lines.append(item["stdout"][:400])
            elif item.get("error"):
                lines.append(item["error"])

        return "\n".join(lines)
