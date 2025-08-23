import asyncio
import os
import json
import redis.asyncio as redis
from src.services.conversation_history import conversation_service
import pytest

# Set up test user and message
test_user_id = "test_redis_user"
test_username = "redis_tester"
test_message = "Hello, this is a Redis cache test!"
test_response = "Hi, Redis is working!"
test_intent = "test_intent"


@pytest.mark.asyncio
async def test_redis_cache():
    await conversation_service.initialize()  # Ensure Redis is initialized
    # Add a conversation (should save to Redis)
    await conversation_service.add_conversation(
        user_id=test_user_id,
        username=test_username,
        user_message=test_message,
        bot_response=test_response,
        intent=test_intent,
    )

    # Connect to Redis directly
    redis_url = os.environ.get("REDIS_URL") or getattr(
        conversation_service, "redis_url", None
    )
    assert redis_url, "No redis_url configured!"
    r = redis.from_url(redis_url)
    redis_key = f"conversation_history:user:{test_user_id}"

    # Check if the hash key exists and has at least one message
    all_msgs = await r.hgetall(redis_key)
    print(f"Redis hash key: {redis_key}, fields: {len(all_msgs)}")
    assert len(all_msgs) > 0, "No messages found in Redis hash for test user!"

    # Get the most recent message (by timestamp)
    parsed_msgs = []
    for msg_json in all_msgs.values():
        data = json.loads(
            msg_json.decode() if isinstance(msg_json, bytes) else msg_json
        )
        parsed_msgs.append(data)
    parsed_msgs.sort(key=lambda m: m["timestamp"], reverse=True)
    most_recent = parsed_msgs[0]
    print(f"Most recent message: {most_recent}")
    assert most_recent["user_id"] == test_user_id
    assert most_recent["message"] == test_message
    assert most_recent["response"] == test_response
    print("✅ Redis hash cache test passed!")


if __name__ == "__main__":
    asyncio.run(test_redis_cache())
