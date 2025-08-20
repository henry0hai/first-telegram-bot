# src/database/qdrant_client.py
# Qdrant utility for clearing all collections

import httpx
from config.config import config


async def clear_all_qdrant_collections():
    qdrant_api_key = getattr(config, "qdrant_api_key", None)
    qdrant_api_url = config.qdrant_api_url
    headers = {"api-key": qdrant_api_key} if qdrant_api_key else {}
    async with httpx.AsyncClient() as client:
        # Get all collections
        resp = await client.get(f"{qdrant_api_url}/collections", headers=headers)
        resp.raise_for_status()
        collections = resp.json().get("result", {}).get("collections", [])
        for col in collections:
            name = col.get("name")
            if name:
                del_resp = await client.delete(
                    f"{qdrant_api_url}/collections/{name}", headers=headers
                )
                del_resp.raise_for_status()
