import json
import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models.schemas import PlanRequest
from services.planner import TravelPlanner

app = FastAPI(title="Multi-Agent Travel Planner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "travel-planner"}


@app.get("/api/debug")
async def debug():
    key = os.environ.get("travel_planner", "")
    serper = os.environ.get("Serper_Api_Key", "")
    mock_raw = os.environ.get("USE_MOCK_DATA", "")
    return {
        "python": sys.executable,
        "travel_planner_set": bool(key),
        "travel_planner_length": len(key),
        "serper_key_set": bool(serper),
        "USE_MOCK_DATA_env": mock_raw or "(not set)",
        "USE_MOCK_DATA_active": mock_raw.lower() in ("1", "true", "yes"),
    }


@app.post("/api/plan")
async def plan_trip(body: PlanRequest, request: Request):
    planner = TravelPlanner()

    async def event_stream():
        async for event in planner.run(
            user_message=body.message,
            partial_params=body.partial_params,
            conversation_history=body.conversation_history,
        ):
            if await request.is_disconnected():
                break
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
