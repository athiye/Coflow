from __future__ import annotations
import asyncio, difflib, fnmatch, os
from pathlib import Path
from typing import Any
from app.core.config import settings
from app.tools.models import ToolManifest

class ToolExecutor:
    async def execute(self, manifest: ToolManifest, repo_path: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        if manifest.adapter == "builtin":
            return await self._run_builtin(manifest.name, repo_path, arguments)
        return {"ok": False, "tool": manifest.name, "error": "Unsupported adapter"}

    async def _run_builtin(self, tool_name: str, repo_path: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        repo = self._safe_repo(repo_path)
        if tool_name == "list_files":
            return self._list_files(repo, arguments)
        if tool_name == "read_file":
            return self._read_file(repo, arguments)
        if tool_name == "search_files":
            return self._search_files(repo, arguments)
        if tool_name == "apply_patch":
            return self._apply_patch(repo, arguments)
        if tool_name == "run_command":
            return await self._run_command(repo, arguments)
        return {"ok": False, "tool": tool_name, "error": "Unsupported builtin tool"}

    def _safe_repo(self, repo_path: str | None) -> Path:
        repo = Path(repo_path or ".").resolve()
        if not repo.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo}")
        return repo

    def _resolve_target(self, repo: Path, rel_path: str) -> Path:
        target = (repo / rel_path).resolve()
        if os.path.commonpath([str(repo), str(target)]) != str(repo):
            raise PermissionError("Path escapes repository root")
        return target

    def _list_files(self, repo: Path, arguments: dict[str, Any]) -> dict[str, Any]:
        pattern = arguments.get("pattern", "*")
        ignore_dirs = {".git","node_modules",".venv","__pycache__","dist","build",".next"}
        results = []
        for file_path in repo.rglob("*"):
            if len(results) >= settings.max_repo_files:
                break
            if any(part in ignore_dirs for part in file_path.parts):
                continue
            if file_path.is_file():
                rel = str(file_path.relative_to(repo))
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    results.append(rel)
        return {"ok": True, "tool": "list_files", "files": results}

    def _read_file(self, repo: Path, arguments: dict[str, Any]) -> dict[str, Any]:
        rel_path = arguments.get("path")
        if not rel_path:
            return {"ok": False, "tool": "read_file", "error": "Missing path"}
        target = self._resolve_target(repo, rel_path)
        if not target.exists() or not target.is_file():
            return {"ok": False, "tool": "read_file", "error": "File not found"}
        return {"ok": True, "tool": "read_file", "path": rel_path, "content": target.read_text(encoding="utf-8", errors="replace")[:settings.max_file_bytes]}

    def _search_files(self, repo: Path, arguments: dict[str, Any]) -> dict[str, Any]:
        query = (arguments.get("query") or "").lower().strip()
        if not query:
            return {"ok": False, "tool": "search_files", "error": "Missing query"}
        ignore_dirs = {".git","node_modules",".venv","__pycache__","dist","build",".next"}
        results = []
        for file_path in repo.rglob("*"):
            if len(results) >= 20:
                break
            if any(part in ignore_dirs for part in file_path.parts) or not file_path.is_file():
                continue
            rel = str(file_path.relative_to(repo))
            if query in rel.lower():
                results.append({"path": rel, "line": None, "snippet": rel})
                continue
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, start=1):
                if query in line.lower():
                    results.append({"path": rel, "line": i, "snippet": line[:240]})
                    break
        return {"ok": True, "tool": "search_files", "results": results}

    def _apply_patch(self, repo: Path, arguments: dict[str, Any]) -> dict[str, Any]:
        rel_path = arguments.get("path")
        if not rel_path:
            return {"ok": False, "tool": "apply_patch", "error": "Missing path"}
        target = self._resolve_target(repo, rel_path)
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        if "replace_all_with" in arguments:
            after = str(arguments["replace_all_with"])
        elif "find" in arguments and "replace" in arguments:
            after = before.replace(str(arguments["find"]), str(arguments["replace"]), 1)
        else:
            return {"ok": False, "tool": "apply_patch", "error": "Provide replace_all_with or find+replace"}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(after, encoding="utf-8")
        diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=f"a/{rel_path}", tofile=f"b/{rel_path}"))
        return {"ok": True, "tool": "apply_patch", "path": rel_path, "diff": diff}

    async def _run_command(self, repo: Path, arguments: dict[str, Any]) -> dict[str, Any]:
        command_text = (arguments.get("command") or "").strip()
        if not settings.allow_shell_commands:
            return {"ok": False, "tool": "run_command", "error": "Shell execution disabled"}
        if not command_text:
            return {"ok": False, "tool": "run_command", "error": "Missing command"}
        parts = command_text.split()
        if parts[0] not in settings.allowed_command_prefix_list:
            return {"ok": False, "tool": "run_command", "error": f"Command prefix not allowed: {parts[0]}"}
        process = await asyncio.create_subprocess_exec(*parts, cwd=str(repo), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.command_timeout_seconds)
        except asyncio.TimeoutError:
            process.kill()
            return {"ok": False, "tool": "run_command", "error": "Command timed out"}
        return {"ok": process.returncode == 0, "tool": "run_command", "command": command_text, "returncode": process.returncode, "stdout": stdout.decode(errors="replace")[:4000], "stderr": stderr.decode(errors="replace")[:4000]}
