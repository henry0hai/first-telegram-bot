# src/handlers/mcp_messages.py - MCP-enhanced message handlers
import aiohttp
from typing import Tuple

from telegram import Update
from telegram.ext import ContextTypes
from config.config import config
from src.ai.mcp_processor import process_for_mcp_ai, IntentType
from src.ai.mcp_request_preprocessor import preprocess_for_mcp_server
from src.handlers.scheduler_handler import handle_scheduler_command
from src.handlers.conversation_commands import handle_clear_intent_in_message
from src.services.conversation_history import conversation_service
from src.services.conversation_processor import conversation_processor
from src.services.qdrant_conversation_manager import qdrant_conversation_manager
from src.utils.logging_utils import get_logger

from datetime import datetime, timezone

timestamp = datetime.now(timezone.utc)

CONFIDENCE_CONTEXT_THRESHOLD = 0.3  # Threshold for using conversation context
logger = get_logger(__name__)


# MCP-enhanced text handler
async def handle_mcp_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced text handler that uses MCP AI preprocessing with conversation history"""
    user_input = update.message.text
    user_id = str(update.message.from_user.id)
    username = update.message.from_user.username or "Unknown"

    message_id = conversation_service._get_message_id(user_id, timestamp)

    try:
        # Check if user wants to clear conversation history
        if await handle_clear_intent_in_message(update, context):
            return  # Early exit if clear intent was handled

        # Get intelligent conversation context using the enhanced processor
        conversation_context_data = (
            await conversation_processor.process_conversation_for_context(
                user_id=user_id, current_message=user_input, max_context_length=3000
            )
        )

        conversation_context = conversation_context_data.get("context_text", "")
        context_summary = conversation_context_data.get("context_summary", "")
        relevant_topics = conversation_context_data.get("relevant_topics", [])
        confidence_score = conversation_context_data.get("confidence_score", 0.0)

        # Detect if this is a direct scheduler command (skip context enhancement for these)
        direct_scheduler = any(
            kw in user_input.lower()
            for kw in [
                "alarm",
                "remind",
                "reminder",
                "schedule",
                "notify",
                "notification",
                "alert",
                "timer",
                "after",
                "every",
                "recurring",
                "repeat",
                "set",
                "cancel task",
                "list tasks",
                "my tasks",
                "wake me",
                "stand up",
                "take water",
                "break",
                "meeting",
                "appointment",
                "deadline",
            ]
        )

        # Improved detection: context is only used if it's non-empty, confidence is above threshold, and not a direct scheduler command
        context_used = False
        enhanced_input = user_input
        if (
            conversation_context
            and confidence_score > CONFIDENCE_CONTEXT_THRESHOLD
            and not direct_scheduler
        ):
            enhanced_input = (
                f"{conversation_context}\n### Current Message:\n{user_input}"
            )
            context_used = True
            logger.info(
                f"Enhanced context for {username}: {len(conversation_context)} chars, "
                f"confidence: {confidence_score:.2f}, topics: {relevant_topics[:3]}"
            )

        # Process with MCP AI preprocessing (using enhanced input for better context awareness)
        mcp_result = process_for_mcp_ai(enhanced_input)
        # But keep original user input in the result for webhook
        mcp_result["original_user_input"] = user_input

        # Contextual fallback: if scheduler was falsely triggered by generic words and
        # we have strong conversation context, prefer RAG for follow-up phrases.
        try:
            text_lower = user_input.lower()
            follow_up = any(
                phrase in text_lower
                for phrase in [
                    "tell me more",
                    "tell me more about",
                    "more about",
                    "explain more",
                    "could you elaborate",
                    "what about",
                ]
            )
            if (
                mcp_result["intent"] == IntentType.RAG_QUERY
                and follow_up
                and confidence_score > CONFIDENCE_CONTEXT_THRESHOLD
            ):
                logger.info(
                    "Overriding scheduler intent to RAG due to follow-up phrase and strong context"
                )
                mcp_result["intent"] = IntentType.RAG_QUERY
                # Carry the original query as the RAG query
                mcp_result["context"] = {
                    "query": user_input,
                    "reason": "contextual_follow_up",
                }
        except Exception:
            pass

        logger.info(
            f"MCP processed query - Intent: {mcp_result['intent'].value}, User: {username}"
        )

        # Send immediate feedback for DYNAMIC_TOOL requests (before preprocessing)
        if mcp_result["intent"] == IntentType.DYNAMIC_TOOL:
            await update.message.reply_text(
                "🛠️ Creating and executing your custom script..."
            )

        # Handle scheduler requests directly (no webhook needed for local scheduling)
        if mcp_result["intent"] == IntentType.TASK_SCHEDULER:
            await handle_scheduler_command(update, context, mcp_result["context"])
            return  # Exit early for scheduler commands

        # Handle dynamic tool requests with preprocessing (user already got feedback)
        if mcp_result["intent"] == IntentType.DYNAMIC_TOOL:
            success, preprocessed_data = await _handle_dynamic_tool_request_enhanced(
                update, context, mcp_result, user_input, user_id
            )

            # Use preprocessed data for webhook if preprocessing was successful
            if success and preprocessed_data.get("success", False):
                logger.info("Using preprocessed MCP request for webhook")
                # Update the payload with preprocessed request
                mcp_result["preprocessed"] = {
                    "tool_calls": preprocessed_data.get("tool_calls", []),
                    "reasoning": preprocessed_data.get("reasoning", ""),
                    "model_used": preprocessed_data.get("model_used", "deepseek-r1:7b"),
                }
            else:
                logger.info("Using basic preprocessing fallback")

        # Send enhanced payload to N8N webhook if configured
        webhook_url = config.n8n_webhook_url
        if webhook_url:
            payload = {
                "message": {
                    "text": mcp_result.get(
                        "original_user_input", user_input
                    ),  # Use original input for webhook
                    "enhanced_text": (enhanced_input if context_used else None),
                    "context_used": context_used,
                    "conversation_context": {
                        "has_context": bool(conversation_context),
                        "context_messages_count": conversation_context_data.get(
                            "messages_count", 0
                        ),
                        "confidence_score": confidence_score,
                        "relevant_topics": relevant_topics,
                        "context_summary": context_summary,
                        "context_text": (
                            conversation_context
                            if len(conversation_context) < 2000
                            else conversation_context[:2000] + "...[truncated]"
                        ),
                    },
                    "mcp_enhanced": {
                        "intent": mcp_result["intent"].value,
                        "context": mcp_result["context"],
                        "mcp_prompt": mcp_result["mcp_prompt"],
                        "original_query": mcp_result["original_query"],
                    },
                },
                "user": {"id": user_id, "username": username},
            }

            # Add preprocessed data to payload if available
            if "preprocessed" in mcp_result:
                payload["message"]["mcp_enhanced"]["preprocessed"] = mcp_result[
                    "preprocessed"
                ]
                logger.info(
                    f"Enhanced payload with {len(mcp_result['preprocessed'].get('tool_calls', []))} preprocessed tool calls"
                )

            try:
                # Debug: Log the actual payload being sent
                logger.info(
                    f"Sending webhook payload for intent {mcp_result['intent'].value}:"
                )
                logger.info(f"Payload keys: {list(payload.keys())}")
                logger.info(f"Message keys: {list(payload['message'].keys())}")
                if "mcp_enhanced" in payload["message"]:
                    logger.info(
                        f"MCP enhanced keys: {list(payload['message']['mcp_enhanced'].keys())}"
                    )

                # Handle to prepare payload include REDIS here
                redis_payload = {
                    "user_id": user_id,
                    "message_id": message_id,
                }
                payload["redis"] = redis_payload

                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload) as resp:
                        webhook_response = ""
                        if resp.status != 200:
                            logger.warning(f"N8N webhook returned status {resp.status}")
                            webhook_response = f"Webhook error: {resp.status}"
                        else:
                            logger.info(
                                f"Successfully sent MCP-enhanced payload to N8N"
                            )
                            try:
                                response_data = await resp.text()
                                webhook_response = (
                                    response_data or "Processed successfully"
                                )
                            except:
                                webhook_response = "Processed successfully"

                        # Store conversation with webhook response
                        await conversation_service.add_conversation(
                            user_id=user_id,
                            username=username,
                            user_message=user_input,
                            bot_response=webhook_response,
                            intent=mcp_result["intent"].value,
                            message_id=message_id,
                        )

                        # ENHANCED: Also store in comprehensive Qdrant for MCP server access
                        await qdrant_conversation_manager.store_conversation(
                            user_id=user_id,
                            username=username,
                            user_message=user_input,
                            response=webhook_response,
                            intent=mcp_result["intent"].value,
                            context_used=bool(
                                conversation_context
                                and confidence_score > CONFIDENCE_CONTEXT_THRESHOLD
                            ),
                            conversation_turn=conversation_context_data.get(
                                "messages_count", 0
                            ),
                            message_id=message_id,
                        )

                        logger.info(
                            f"Caching conversation for {user_id} with message ID {message_id} successful."
                        )

            except Exception as e:
                logger.error(f"Failed to send to N8N webhook: {e}")
                # Store conversation even if webhook fails
                await conversation_service.add_conversation(
                    user_id=user_id,
                    username=username,
                    user_message=user_input,
                    bot_response=f"Webhook error: {str(e)}",
                    intent=mcp_result["intent"].value,
                    message_id=message_id,
                )

                # ENHANCED: Also store in comprehensive Qdrant for MCP server access
                await qdrant_conversation_manager.store_conversation(
                    user_id=user_id,
                    username=username,
                    user_message=user_input,
                    response=f"Webhook error: {str(e)}",
                    intent=mcp_result["intent"].value,
                    context_used=bool(
                        conversation_context
                        and confidence_score > CONFIDENCE_CONTEXT_THRESHOLD
                    ),
                    conversation_turn=conversation_context_data.get(
                        "messages_count", 0
                    ),
                    message_id=message_id,
                )

        # Provide user feedback for other intents (DYNAMIC_TOOL already got immediate feedback)
        intent_messages = {
            IntentType.RAG_QUERY: "🔍 Processing your document-related question...",
            IntentType.SEARCH_QUERY: "🌐 Searching for the latest information...",
            IntentType.SYSTEM_INFO: "💻 Getting system information...",
            IntentType.WEATHER: f"🌤️ Getting weather information...",
            IntentType.BUDGET_FINANCE: "💰 Processing your budget/finance request...",
            IntentType.EMAIL_COMMUNICATION: "📧 Handling your email request...",
            IntentType.TRANSLATION_LANGUAGE: "🌍 Processing translation request...",
            IntentType.TASK_SCHEDULER: "⏰ Creating your scheduled task...",
            IntentType.UNKNOWN: "🤖 Processing your request...",
        }

        feedback_message = intent_messages.get(
            mcp_result["intent"], intent_messages[IntentType.UNKNOWN]
        )

        # Add conversation context info to feedback if relevant
        if conversation_context and confidence_score > CONFIDENCE_CONTEXT_THRESHOLD:
            msg_count = conversation_context_data.get("messages_count", 0)
            feedback_message += f"\n\n📚 *Using context from {msg_count} previous messages (confidence: {confidence_score:.1f})*"

        await update.message.reply_text(feedback_message, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in handle_mcp_text: {e}")
        await update.message.reply_text(
            "❌ Sorry, I encountered an error processing your message. Please try again."
        )


async def _handle_dynamic_tool_request_enhanced(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mcp_result: dict,
    user_input: str,
    user_id: int,
) -> Tuple[bool, dict]:
    """
    Enhanced dynamic tool creation request handler with MCP request preprocessing

    This preprocesses user queries into structured MCP tool calls before sending
    to webhook, allowing the MCP server to easily select the correct tools.
    No Telegram message is sent - preprocessing is silent.
    """
    tool_context = mcp_result["context"]
    query = tool_context.get("query", "")
    tool_type = tool_context.get("tool_type", "auto")
    chat_id = str(update.effective_chat.id)

    logger.info(f"Preprocessing DYNAMIC_TOOL request (silent): {tool_type}")

    # Preprocess the request for better MCP server handling - FIXED TUPLE HANDLING
    # Pass the full mcp_result (which contains intent) instead of just tool_context
    ai_success, preprocessed_result = preprocess_for_mcp_server(user_input, mcp_result)

    # Log the preprocessing result but don't send to Telegram
    if ai_success and preprocessed_result.get("success", False):
        tool_calls = preprocessed_result.get("tool_calls", [])
        tool_name = tool_calls[0]["function"]["name"] if tool_calls else "unknown"
        logger.info(
            f"Preprocessed with {preprocessed_result.get('model_used')}: {tool_name}"
        )
    else:
        logger.info("Using fallback preprocessing (AI unavailable)")

    # Return the preprocessed result for webhook enhancement (no Telegram message)
    return True, preprocessed_result
