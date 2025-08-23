# src/rest_server.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.services.conversation_history import conversation_service
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conversation_service.initialize()
    yield


app = FastAPI(lifespan=lifespan)


class UpdateConversationRequest(BaseModel):
    user_id: str
    message_id: str  # UUID5 used as Redis hash field
    response: str


@app.post("/update_conversation_response")
async def update_conversation_response(req: UpdateConversationRequest):
    redis_key = conversation_service._get_redis_key(req.user_id)
    # Fetch the message from Redis hash
    msg_json = await conversation_service.redis_client.hget(redis_key, req.message_id)
    if not msg_json:
        raise HTTPException(status_code=404, detail="Message not found in Redis")
    # Update the response field
    import json

    msg = json.loads(msg_json.decode() if isinstance(msg_json, bytes) else msg_json)
    msg["bot_response"] = req.response
    # Save back to Redis
    await conversation_service.redis_client.hset(
        redis_key, req.message_id, json.dumps(msg)
    )
    return {"status": "success"}
