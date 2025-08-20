# src/handlers/messages.py - Regular message handlers
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
from config.config import config
from src.database.qdrant_client import clear_all_qdrant_collections
from src.ai.ai_processor import process_with_ai
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


# Regular text handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"

    # Send to N8N webhook if configured
    webhook_url = config.n8n_webhook_url
    if webhook_url:
        payload = {
            "message": {
                "text": user_input,
            },
            "user": {"id": user_id, "username": username},
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(f"N8N webhook returned status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send to N8N webhook: {e}")

    # Process with AI
    response = await process_with_ai(user_input, update, context)
    if response is not None and response.strip():
        await update.message.reply_text(response)
    elif response is not None:
        logger.warning(
            f"Empty response received for input '{user_input}' from {username} ({user_id})"
        )


# Photo handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    photos = update.message.photo
    file_id = photos[0].file_id if photos else None
    caption = update.message.caption if hasattr(update.message, "caption") else None

    # Send to N8N webhook if configured
    webhook_url = config.n8n_webhook_url
    if webhook_url and file_id:
        message_payload = {
            "photo": [{"file_id": file_id}],
        }
        if caption:
            message_payload["caption"] = caption
        payload = {
            "message": message_payload,
            "user": {"id": user_id, "username": username},
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"N8N webhook returned status {resp.status} for photo"
                        )
        except Exception as e:
            logger.error(f"Failed to send photo to N8N webhook: {e}")

    # Reply to user
    if file_id:
        reply = f"Received your photo! file_id: {file_id}"
        if caption:
            reply += f"\nCaption: {caption}"
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("No photo found in the message.")


# Document handler
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"
    document = update.message.document
    file_id = document.file_id if document else None
    file_name = document.file_name if document else None
    caption = update.message.caption if hasattr(update.message, "caption") else None

    # Clear all collection in QDRANT first before continue
    try:
        await clear_all_qdrant_collections()
        logger.info("Cleared all Qdrant collections before handling document upload.")
    except Exception as e:
        logger.error(f"Failed to clear Qdrant collections: {e}")

    # Send to N8N webhook if configured
    webhook_url = config.n8n_webhook_url
    if webhook_url and file_id:
        message_payload = {
            "document": {
                "file_id": file_id,
                "file_name": file_name,
                "caption": caption,
            }
        }
        payload = {
            "message": message_payload,
            "user": {"id": user_id, "username": username},
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"N8N webhook returned status {resp.status} for document"
                        )
        except Exception as e:
            logger.error(f"Failed to send document to N8N webhook: {e}")

    # Reply to user
    if file_id:
        reply = f"Received your document! file_id: {file_id}"
        if file_name:
            reply += f"\nFile name: {file_name}"
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("No document found in the message.")
