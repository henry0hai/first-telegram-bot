# src/handlers/conversation_commands.py
"""
Conversation Management Commands

Handles commands related to conversation history management:
- /clear_conversation - Clear conversation history
- /conversation_status - Show conversation statistics
"""

from telegram import Update
from telegram.ext import ContextTypes
from src.services.conversation_history import conversation_service
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


async def clear_conversation_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Command to clear conversation history"""
    try:
        user_id = str(update.message.from_user.id)
        username = update.message.from_user.username or "Unknown"

        # Clear conversation history
        await conversation_service.clear_conversation_history(user_id)

        await update.message.reply_text(
            "🗑️ **Conversation Cleared**\n\n"
            "Your conversation history has been successfully cleared from both cache and long-term storage.\n"
            "Starting fresh! 🌟"
        )

        logger.info(f"Cleared conversation history for user {username} ({user_id})")

    except Exception as e:
        logger.error(f"Failed to clear conversation history: {e}")
        await update.message.reply_text(
            "❌ **Error**\n\n"
            "Sorry, I couldn't clear your conversation history right now. Please try again later."
        )


async def conversation_status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Command to show conversation statistics"""
    try:
        user_id = str(update.message.from_user.id)
        username = update.message.from_user.username or "Unknown"

        # Get conversation summary
        summary = await conversation_service.get_conversation_summary(user_id)

        if "error" in summary:
            await update.message.reply_text(
                "❌ **Error**\n\n"
                f"Could not retrieve conversation statistics: {summary['error']}"
            )
            return

        # Format response
        response_lines = [
            "📊 **Conversation Statistics**\n",
            f"👤 **User:** {username}",
            f"💬 **Recent Messages:** {summary.get('recent_messages_count', 0)} (cached)",
            f"📚 **Total Messages:** {summary.get('total_messages_count', 0)} (stored)",
        ]

        if summary.get("last_conversation"):
            response_lines.append(f"🕒 **Last Chat:** {summary['last_conversation']}")

        response_lines.extend(
            [
                "",
                "**Available Commands:**",
                "• `/clear_conversation` - Clear all history",
                "• `/conversation_status` - Show this info",
            ]
        )

        await update.message.reply_text("\n".join(response_lines))

        logger.info(f"Showed conversation status for user {username} ({user_id})")

    except Exception as e:
        logger.error(f"Failed to get conversation status: {e}")
        await update.message.reply_text(
            "❌ **Error**\n\n"
            "Sorry, I couldn't retrieve your conversation statistics right now. Please try again later."
        )


async def handle_clear_intent_in_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Check if user message contains clear intent and handle it
    Returns True if clear intent was detected and handled
    """
    try:
        user_message = update.message.text

        # Check if message contains clear intent
        if conversation_service.detect_clear_intent(user_message):
            user_id = str(update.message.from_user.id)
            username = update.message.from_user.username or "Unknown"

            # Clear conversation history
            await conversation_service.clear_conversation_history(user_id)

            await update.message.reply_text(
                "🗑️ **Understood!**\n\n"
                "I've cleared our conversation history as requested. "
                "We're starting with a clean slate! 🌟\n\n"
                "What would you like to talk about?"
            )

            logger.info(
                f"Auto-cleared conversation history for user {username} ({user_id}) based on message intent"
            )
            return True

    except Exception as e:
        logger.error(f"Failed to handle clear intent: {e}")

    return False
