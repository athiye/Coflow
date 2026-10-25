import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.agents.swe_agent import SWEAgent
from app.agents.computer_use_agent import ComputerUseAgent
from app.core.prompt_library import PROMPT_ACTIONS, is_computer_use_action
from app.core.schemas import ChatRequest, ChatResponse, ToolListResponse
from app.tools.registry import ToolRegistry

router = APIRouter()
agent = SWEAgent()
computer_agent = ComputerUseAgent()
tool_registry = ToolRegistry()

def _pick_agent(request: ChatRequest):
    if is_computer_use_action(request.action_key) or (request.computer_use and request.computer_use.start_url):
        return computer_agent
    return agent

@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        chosen = _pick_agent(request)
        return await chosen.handle(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/api/chat/stream")
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    async def event_generator():
        try:
            chosen = _pick_agent(request)
            async for event in chosen.stream_handle(request):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'data': str(exc)})}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/api/tools", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    return ToolListResponse(tools=tool_registry.list_tools())

@router.get("/api/actions")
async def list_actions():
    return {"actions": PROMPT_ACTIONS}
