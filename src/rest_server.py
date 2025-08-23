# src/rest_server.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.services.conversation_history import conversation_service
from src.services.qdrant_conversation_manager import qdrant_conversation_manager
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await conversation_service.initialize()
    await qdrant_conversation_manager.initialize()
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
    msg["response"] = req.response
    # Save back to Redis
    try:
        await conversation_service.redis_client.hset(
            redis_key, req.message_id, json.dumps(msg)
        )
        logger.info(f"Updated response in Redis for message_id: {req.message_id}")
    except Exception as e:
        logger.warning(f"Failed to update Redis for message_id {req.message_id}: {e}")

    # Also update Qdrant with the new response
    try:
        await qdrant_conversation_manager.update_conversation_response(
            message_id=req.message_id, new_response=req.response
        )
        logger.info(
            f"Updated response in Qdrant for message_id: {req.message_id}"
        )
    except Exception as e:
        logger.warning(f"Failed to update Qdrant for message_id {req.message_id}: {e}")
        # Don't fail the request if only Qdrant update fails

    return {"status": "success"}
