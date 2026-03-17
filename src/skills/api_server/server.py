# ============================================================
# skills/api_server/server.py — FastAPI REST API + SSE Streaming
#
# Session-aware API with gateway integration.
# All routes go through core/gateway.py for unified sessions.
# ============================================================

import os
import json
import threading
from settings import settings as config
from skills.logger import log_audit, log_app

_server_thread = None


def create_app():
    """Create the FastAPI application with gateway integration."""
    from fastapi import FastAPI, HTTPException, Request, Depends, Security
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from fastapi.security import APIKeyHeader
    from core.auth import validate_api_key
    from pydantic import BaseModel

    app = FastAPI(title="ASURA - Self-Updating AI", version="4.0", description="Sovereign AI Agent API")
    
    # Restrict CORS Origins - use config if available, fallback to localhost
    cors_origins = getattr(config, "ALLOWED_CORS_ORIGINS", ["http://localhost:3000", "http://127.0.0.1:3000"])
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_methods=["GET", "POST"], allow_headers=["*"])

    class ChatRequest(BaseModel):
        message: str
        stream: bool = False

    class RunRequest(BaseModel):
        command: str
        timeout: int = 30

    class SummarizeRequest(BaseModel):
        text: str = ""
        url: str = ""
        style: str = "bullets"

    class ReviewRequest(BaseModel):
        filepath: str = ""
        code: str = ""

    def _get_session_id(request: Request) -> str:
        """Extract session ID from header or generate one."""
        return request.headers.get("X-ASURA-Session", f"api_{request.client.host}")

    header_scheme = APIKeyHeader(name="X-ASURA-Key", auto_error=False)

    async def verify_api_key(request: Request, api_key: str = Security(header_scheme)):
        if not api_key:
            api_key = request.query_params.get("key")
        
        if not api_key or not validate_api_key(api_key):
            # Allow /health and /voice/health without key if desired, but here we protect mostly everything
            if request.url.path in ["/health", "/voice/health"]:
                return None
            raise HTTPException(status_code=401, detail="Invalid Sovereign API Key")
        return api_key

    # ── Health ────────────────────────────────────────────────
    @app.get("/health")
    def health():
        from skills.hardware_monitor import get_system_info
        return {"status": "ok", "system": get_system_info()}

    # ── Skills ────────────────────────────────────────────────
    @app.get("/skills")
    def skills():
        from skills.skill_registry import discover_skills
        registry = discover_skills()
        return {"count": len(registry), "skills": list(registry.keys())}

    # ── Tools (MCP) ───────────────────────────────────────────
    @app.get("/tools", dependencies=[Depends(verify_api_key)])
    def tools():
        from core.tool_protocol import get_tools_schema, get_tool_count
        return {"count": get_tool_count(), "tools": get_tools_schema()}

    # ── Chat (Sync — via Gateway) ─────────────────────────────
    @app.post("/chat", dependencies=[Depends(verify_api_key)])
    async def chat(req: ChatRequest, request: Request):
        from core.gateway import handle_message, handle_command
        session_id = _get_session_id(request)

        # Check for gateway commands
        if req.message.startswith("/"):
            result = await handle_command(session_id, req.message, channel="api")
            if result is not None:
                return {"response": result, "session_id": session_id}

        if req.stream:
            # SSE Streaming
            async def event_stream():
                gen = await handle_message(session_id, req.message, channel="api", stream=True)
                # handle_message returns a Generator, but in async mode it should return an AsyncGenerator or we wrap it
                # Since handle_message is now async, it returns a coroutine. 
                # Wait, I changed handle_message to async def.
                res = await gen
                if hasattr(res, "__aiter__"):
                    async for chunk in res:
                        data = json.dumps({"chunk": chunk})
                        yield f"data: {data}\n\n"
                else:
                    # Non-streaming result returned as single chunk
                    yield f"data: {json.dumps({'chunk': res})}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-ASURA-Session": session_id},
            )

        reply = await handle_message(session_id, req.message, channel="api", stream=False)
        return {"response": reply, "session_id": session_id}

    # ── Sessions ──────────────────────────────────────────────
    @app.get("/sessions", dependencies=[Depends(verify_api_key)])
    async def sessions():
        from core.gateway import list_sessions, get_session_count
        return {"count": get_session_count(), "sessions": list_sessions()}

    # ── Stats (Observability) ─────────────────────────────────
    @app.get("/stats", dependencies=[Depends(verify_api_key)])
    def stats():
        try:
            from core.observability import get_session_stats, get_recent_traces
            return {
                "session": get_session_stats(),
                "recent_traces": get_recent_traces(5),
            }
        except Exception as e:
            log_app(f"Stats Error: {e}")
            return {"error": "Internal server error while fetching stats."}

    # ── Run Shell ─────────────────────────────────────────────
    @app.post("/run", dependencies=[Depends(verify_api_key)])
    async def run_command(req: RunRequest):
        from skills.shell_executor.executor import execute
        try:
            result = await execute(req.command, timeout=req.timeout)
            return result
        except Exception as e:
            log_app(f"API Run Error: {e}")
            raise HTTPException(500, "Command execution failed.")

    # ── Summarize ─────────────────────────────────────────────
    @app.post("/summarize", dependencies=[Depends(verify_api_key)])
    def summarize(req: SummarizeRequest):
        from skills.doc_summarizer import summarize_text, summarize_url
        if req.url:
            return {"summary": summarize_url(req.url, req.style)}
        return {"summary": summarize_text(req.text, req.style)}

    @app.post("/review", dependencies=[Depends(verify_api_key)])
    async def review(req: ReviewRequest):
        from skills.swarm_review import review_file, review_code
        if req.filepath:
            return {"review": await review_file(req.filepath)}
        return {"review": await review_code(req.code)}

    # ── TODOs ─────────────────────────────────────────────────
    @app.get("/todos", dependencies=[Depends(verify_api_key)])
    def todos():
        from skills.todo_manager import get_open_todos
        return {"todos": get_open_todos()}

    # ── Calendar ──────────────────────────────────────────────
    @app.get("/calendar", dependencies=[Depends(verify_api_key)])
    def calendar():
        from skills.calendar_manager import get_upcoming
        return {"events": get_upcoming()}

    # ── Memory Search ─────────────────────────────────────────
    @app.get("/memory/search", dependencies=[Depends(verify_api_key)])
    def memory_search(q: str):
        from skills.memory import recall
        results = recall(q)
        return {"query": q, "results": results}

    # ── Knowledge Graph ───────────────────────────────────────
    @app.get("/knowledge", dependencies=[Depends(verify_api_key)])
    def knowledge(q: str = ""):
        from skills.knowledge_graph import search_nodes, get_graph_stats
        if q:
            return {"results": search_nodes(q)}
        return {"stats": get_graph_stats()}

    # ── Evolve ────────────────────────────────────────────────
    @app.post("/evolve", dependencies=[Depends(verify_api_key)])
    async def evolve():
        from core.self_updater import SelfUpdater
        result = SelfUpdater().evolve()
        return result

    # ── Workflows ─────────────────────────────────────────────
    @app.get("/workflows", dependencies=[Depends(verify_api_key)])
    def workflows():
        from core.workflow_engine import list_workflows
        return {"workflows": list_workflows()}

    @app.post("/workflows/{name}", dependencies=[Depends(verify_api_key)])
    def run_workflow(name: str):
        from core.workflow_engine import run_workflow
        return run_workflow(name)

    # ── Cancel ────────────────────────────────────────────────
    @app.post("/cancel", dependencies=[Depends(verify_api_key)])
    def cancel():
        from skills.ai_content.generator import cancel_current_task
        cancel_current_task()
        return {"status": "cancelled"}

    # ── Voice Chat ─────────────────────────────────────────────
    @app.post("/voice", dependencies=[Depends(verify_api_key)])
    async def voice_chat(request: Request):
        """Accept audio, transcribe, get AI response, return audio."""
        from fastapi import UploadFile, File
        from fastapi.responses import Response as FastAPIResponse

        form = await request.form()
        audio_file = form.get("audio")
        if not audio_file:
            raise HTTPException(400, "Missing 'audio' file in form data")

        audio_bytes = await audio_file.read()
        session_id = _get_session_id(request)

        from skills.voice_chat.pipeline import voice_chat_single
        response_audio = voice_chat_single(audio_bytes, user_id=session_id)

        return FastAPIResponse(
            content=response_audio,
            media_type="audio/wav",
            headers={"X-ASURA-Session": session_id},
        )

    @app.get("/voice/health")
    def voice_health():
        from skills.voice_chat.client import check_health
        return check_health()

    return app


def start_api_server():
    """Start the API server in a background thread."""
    global _server_thread

    def run():
        import uvicorn
        app = create_app()
        log_app(f"API server starting on {config.API_HOST}:{config.API_PORT}")
        uvicorn.run(app, host=config.API_HOST, port=config.API_PORT, log_level="warning")

    _server_thread = threading.Thread(target=run, daemon=True, name="api-server")
    _server_thread.start()
    log_audit("API", f"Server started on port {config.API_PORT}")
