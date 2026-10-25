from __future__ import annotations
import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List

from app.computer_use.browser_harness import BrowserHarness
from app.providers.factory import ProviderFactory
from app.core.config import settings
from app.core.schemas import ChatResponse, ToolCall


CHUNK_SIZE = 5


class ComputerUseAgent:
    def __init__(self):
        self.provider = ProviderFactory.get("openai_responses")
        self.harness = BrowserHarness()

    async def handle(self, request):
        goal = self._extract_goal(request)
        start_url = request.computer_use.start_url
        max_steps = getattr(request.computer_use, "max_steps", None) or settings.computer_use_max_steps
        step_delay = getattr(settings, "computer_use_step_delay_ms", 1500)
        app_name = getattr(request.computer_use, "app_name", None)

        await self.harness.start()
        page = await self.harness.new_page()
        await self.harness.goto(page, start_url)

        history: List[Dict[str, Any]] = []
        chunks: List[List[Dict[str, Any]]] = []
        current_chunk: List[Dict[str, Any]] = []
        action_trace: List[Dict[str, Any]] = []
        current_url = start_url

        try:
            for step in range(max_steps):
                print(f"[computer-use] Step {step + 1}")

                snapshot = await self.harness.capture_current_page(page, app_name=app_name, step=step + 1)
                page_data = snapshot.to_dict()

                history.append({
                    "url": current_url,
                    "title": page_data["title"],
                })
                current_chunk.append(page_data)

                if len(current_chunk) == CHUNK_SIZE:
                    chunks.append(current_chunk)
                    current_chunk = []

                action_raw = await self.decide_next_action(goal, history, page_data)
                action = self.parse_action(action_raw)
                action_trace.append(action)

                if action.get("action", "STOP") == "STOP":
                    print("[computer-use] Goal achieved or agent chose to stop.")
                    break

                try:
                    current_url = await self.execute_action_with_retries(page, action, page_data, current_url)
                except Exception as exc:
                    print(f"[computer-use] Action failed: {exc}")

                await asyncio.sleep(step_delay / 1000)

            if current_chunk:
                chunks.append(current_chunk)

            print("[computer-use] Navigation complete. Summarizing...")

            summaries = []
            for chunk in chunks:
                summaries.append(await self.summarize_chunk(chunk))

            final = await self.final_synthesis(goal, summaries, action_trace)

            tool_calls = [
                ToolCall(
                    tool="computer_use_navigation",
                    arguments={
                        "start_url": start_url,
                        "goal": goal,
                        "max_steps": max_steps,
                    },
                    confidence=1.0,
                    source="computer_use",
                )
            ]

            tool_results = [
                {
                    "ok": True,
                    "tool": "computer_use_summary",
                    "chunk_count": len(chunks),
                    "history": history,
                    "actions": action_trace,
                }
            ]

            return ChatResponse(
                route="mid",
                provider=getattr(self.provider, "name", "unknown"),
                model=getattr(settings, "mid_model", "unknown"),
                plan=[
                    "Open the target website.",
                    "Interpret the stated goal and page state.",
                    "Interact with the page using generic robust browser actions.",
                    "Capture evidence, summarize chunks, and synthesize findings.",
                ],
                tool_calls=tool_calls,
                tool_results=tool_results,
                patches=[],
                answer=final,
                metrics={
                    "goal": goal,
                    "start_url": start_url,
                    "steps_attempted": max_steps,
                    "chunks_created": len(chunks),
                },
            )
        finally:
            try:
                await page.close()
            except Exception:
                pass
            await self.harness.close()

    async def stream_handle(self, request) -> AsyncIterator[dict[str, Any]]:
        result = await self.handle(request)
        yield {
            "type": "route",
            "data": {
                "route": result.route,
                "provider": result.provider,
                "model": result.model,
            },
        }
        yield {"type": "plan", "data": result.plan}
        yield {"type": "tool_calls", "data": [x.model_dump() for x in result.tool_calls]}
        if result.patches:
            yield {"type": "patches", "data": result.patches}
        yield {"type": "final", "data": result.model_dump()}

    async def execute_action_with_retries(self, page, action: dict, page_data: dict, current_url: str) -> str:
        attempts = 0
        last_error = None
        current_action = dict(action)

        while attempts < 3:
            try:
                return await self.execute_action(page, current_action, page_data, current_url)
            except Exception as exc:
                last_error = exc
                attempts += 1
                await asyncio.sleep(0.5)

                if attempts == 1 and current_action.get("action") == "CLICK_SELECTOR":
                    current_action = {
                        **current_action,
                        "action": "CLICK_TEXT",
                        "target": current_action.get("target_text") or current_action.get("target", "")
                    }
                elif attempts == 2 and current_action.get("action") in {"CLICK_SELECTOR", "CLICK_TEXT"}:
                    current_action = {
                        **current_action,
                        "action": "CLICK_LINK",
                        "target": current_action.get("target", "")
                    }

        raise last_error if last_error else RuntimeError("Action failed after retries.")

    async def execute_action(self, page, action: dict, page_data: dict, current_url: str) -> str:
        action_type = action.get("action", "STOP")
        target = (action.get("target") or "").strip()
        value = (action.get("value") or "").strip()
        target_text = (action.get("target_text") or target).strip()

        if action_type == "NAVIGATE":
            if target.startswith("http"):
                await self.harness.navigate_page(page, target)
                return target
            return current_url

        if action_type == "CLICK_LINK":
            links = page_data.get("discovered_links", [])
            match = None
            for link in links:
                if target and target.lower() in link.lower():
                    match = link
                    break
            if match:
                await self.harness.navigate_page(page, match)
                return match
            raise RuntimeError(f"No matching link found for target: {target}")

        if action_type == "CLICK_TEXT":
            await self.harness.click_text(page, target_text)
            return getattr(page, "url", current_url)

        if action_type == "CLICK_SELECTOR":
            await self.harness.click_selector(page, target, text_fallback=target_text)
            return getattr(page, "url", current_url)

        if action_type == "TYPE_SELECTOR":
            await self.harness.type_selector(page, target, value, submit=bool(action.get("submit", False)))
            return getattr(page, "url", current_url)

        if action_type == "SEARCH":
            await self.harness.search(page, value or target_text)
            return getattr(page, "url", current_url)

        if action_type == "APPLY_FILTER":
            await self.harness.apply_filter(page, value or target_text)
            return getattr(page, "url", current_url)

        if action_type == "TOGGLE":
            await self.harness.safe_toggle(page, target, desired=bool(action.get("desired", True)), text_fallback=target_text)
            return getattr(page, "url", current_url)

        if action_type == "ADD_TO_CART":
            await self.harness.add_to_cart(page)
            return getattr(page, "url", current_url)

        return current_url

    async def decide_next_action(self, goal, history, current_page):
        prompt = f"""
You are a goal-directed browser automation and UX testing agent.

Goal:
{goal}

Recent history:
{history[-8:]}

Current page:
URL: {current_page.get("url")}
TITLE: {current_page.get("title")}
VISIBLE_TEXT:
{current_page.get("visible_text", "")[:1200]}

CLICKABLE ELEMENTS:
{current_page.get("clickable_elements", [])[:15]}

INPUTS:
{current_page.get("inputs", [])[:10]}

TOGGLES:
{current_page.get("toggles", [])[:10]}

DIALOGS:
{current_page.get("dialogs", [])[:5]}

DISCOVERED LINKS:
{current_page.get("discovered_links", [])[:12]}

Choose the single best next action.

Allowed actions:
- NAVIGATE
- CLICK_LINK
- CLICK_TEXT
- CLICK_SELECTOR
- TYPE_SELECTOR
- SEARCH
- APPLY_FILTER
- TOGGLE
- ADD_TO_CART
- STOP

Return strict JSON:
{{
  "action": "ONE_OF_THE_ACTIONS",
  "reason": "brief reason",
  "target": "url, selector, link fragment, or control identifier",
  "target_text": "visible text to use as fallback if relevant",
  "value": "text to type if needed",
  "submit": false,
  "desired": true
}}
"""
        return await self.safe_call(prompt)

    async def summarize_chunk(self, chunk):
        prompt = f"""
Summarize the key UX and interaction insights from these browser steps.

Pages:
{chunk}

Keep it concise and structured.
"""
        return await self.safe_call(prompt)

    async def final_synthesis(self, goal, summaries, action_trace):
        prompt = f"""
You are a UX and product expert.

Goal:
{goal}

Action trace:
{action_trace[:25]}

Using these summaries:
{summaries}

Return:
- journey overview
- key friction points
- feature gaps
- recommendations
"""
        return await self.safe_call(prompt)

    def parse_action(self, response):
        try:
            if isinstance(response, dict):
                return response
            return json.loads(response)
        except Exception:
            return {"action": "STOP"}

    async def safe_call(self, prompt):
        for attempt in range(3):
            try:
                return await self.provider.complete(
                    "You are a goal-directed browser automation and UX analysis assistant.",
                    prompt,
                    getattr(settings, "mid_model", "gpt-4.1"),
                    {"phase": "computer_use"},
                )
            except Exception as e:
                if "429" in str(e):
                    time.sleep(2 * (attempt + 1))
                else:
                    raise
        return "Error: failed after retries"

    def _extract_goal(self, request) -> str:
        if getattr(request, "computer_use", None) and getattr(request.computer_use, "goal", None):
            return request.computer_use.goal
        if getattr(request, "message", None):
            return request.message
        return "Review the live website experience."
