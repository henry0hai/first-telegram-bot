# src/handlers/scheduler_handler.py - Scheduler-specific message handlers
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from src.services.task_scheduler import task_scheduler
from src.utils.logging_utils import get_logger
from config.config import config

logger = get_logger(__name__)


async def handle_scheduler_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, scheduler_context: dict
):
    """
    Handle scheduler-specific commands based on detected intent

    Args:
        update: Telegram update object
        context: Telegram context
        scheduler_context: Context from MCP processor containing scheduler intent details
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = scheduler_context.get("query", "")
    scheduler_type = scheduler_context.get("scheduler_type", "unknown")

    logger.info(f"Processing scheduler command: {scheduler_type} for user {user_id}")

    try:
        if scheduler_type == "alarm":
            await _handle_create_alarm(update, context, text, user_id, chat_id)
        elif scheduler_type == "reminder":
            await _handle_create_reminder(update, context, text, user_id, chat_id)
        elif scheduler_type == "notification":
            await _handle_create_notification(update, context, text, user_id, chat_id)
        elif scheduler_type == "list":
            await _handle_list_tasks(update, context, user_id)
        elif scheduler_type == "cancel":
            await _handle_cancel_task(update, context, text, user_id)
        else:
            # Try to detect automatically
            await _handle_auto_detect_scheduler(update, context, text, user_id, chat_id)

    except Exception as e:
        logger.error(f"Error handling scheduler command: {e}")
        await update.message.reply_text(
            "❌ Sorry, I encountered an error processing your scheduler request. Please try again."
        )


async def _handle_create_alarm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_id: int,
    chat_id: int,
):
    """Handle creating a one-time alarm"""
    job_queue = context.job_queue

    task_id = task_scheduler.create_alarm(user_id, chat_id, text, job_queue)

    if task_id:
        # Parse delay for confirmation message
        delay_seconds = task_scheduler.parse_time_delay(text)
        if delay_seconds:
            if delay_seconds < 60:
                time_str = f"{delay_seconds} seconds"
            elif delay_seconds < 3600:
                time_str = f"{delay_seconds // 60} minutes"
            else:
                time_str = f"{delay_seconds // 3600} hours"
        else:
            time_str = "the specified time"

        message = task_scheduler.extract_task_message(text)

        await update.message.reply_text(
            f"⏰ **Alarm Set!**\n\n"
            f"🔔 Message: {message}\n"
            f"⏱️ Time: In {time_str}\n"
            f"🆔 Task ID: `{task_id}`\n\n"
            f"💡 Use 'cancel task {task_id}' to cancel this alarm."
        )
    else:
        await update.message.reply_text(
            "❌ I couldn't understand the time format. Try something like:\n"
            "• 'Set alarm after 20 seconds'\n"
            "• 'Wake me up in 30 minutes'\n"
            "• 'Remind me in 2 hours'"
        )


async def _handle_create_reminder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_id: int,
    chat_id: int,
):
    """Handle creating a recurring reminder"""
    job_queue = context.job_queue

    task_id = task_scheduler.create_reminder(user_id, chat_id, text, job_queue)

    if task_id:
        # Parse interval for confirmation message
        interval_seconds = task_scheduler.parse_recurring_interval(text)
        if interval_seconds:
            if interval_seconds < 60:
                interval_str = f"{interval_seconds} seconds"
            elif interval_seconds < 3600:
                interval_str = f"{interval_seconds // 60} minutes"
            else:
                interval_str = f"{interval_seconds // 3600} hours"
        else:
            interval_str = "the specified interval"

        message = task_scheduler.extract_task_message(text)

        await update.message.reply_text(
            f"🔁 **Recurring Reminder Set!**\n\n"
            f"🔔 Message: {message}\n"
            f"⏱️ Interval: Every {interval_str}\n"
            f"🆔 Task ID: `{task_id}`\n\n"
            f"💡 Use 'cancel task {task_id}' to stop this reminder."
        )
    else:
        await update.message.reply_text(
            "❌ I couldn't understand the interval format. Try something like:\n"
            "• 'Remind me every 25 minutes to stand up'\n"
            "• 'Alert me every hour to drink water'\n"
            "• 'Notify me every 2 hours'"
        )


async def _handle_create_notification(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_id: int,
    chat_id: int,
):
    """Handle creating a scheduled notification"""
    job_queue = context.job_queue

    task_id = task_scheduler.create_notification(user_id, chat_id, text, job_queue)

    if task_id:
        # Get scheduled time for confirmation
        scheduled_time = task_scheduler.parse_absolute_time(text)
        time_str = (
            scheduled_time.strftime("%Y-%m-%d %H:%M")
            if scheduled_time
            else "the specified time"
        )

        message = task_scheduler.extract_task_message(text)

        await update.message.reply_text(
            f"📅 **Notification Scheduled!**\n\n"
            f"🔔 Message: {message}\n"
            f"⏰ Time: {time_str}\n"
            f"🆔 Task ID: `{task_id}`\n\n"
            f"💡 Use 'cancel task {task_id}' to cancel this notification."
        )
    else:
        await update.message.reply_text(
            "❌ I couldn't understand the time format. Try something like:\n"
            "• 'Notify me to \"Go to the bank\" next week at 9:00 AM'\n"
            "• 'Schedule reminder at 2:30 PM'\n"
            "• 'Alert me tomorrow at 8:00'"
        )


async def _handle_list_tasks(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
):
    """Handle listing all user tasks"""
    tasks_text = task_scheduler.list_tasks_text(user_id)
    await update.message.reply_text(tasks_text)


async def _handle_cancel_task(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, user_id: int
):
    """Handle canceling a specific task"""
    import re

    # Extract task ID from text
    task_id_match = re.search(r"cancel\s+task\s+([a-zA-Z0-9_\.]+)", text.lower())
    if not task_id_match:
        await update.message.reply_text(
            "❌ Please specify a task ID to cancel.\n\n"
            "Usage: 'cancel task <task_id>'\n"
            "Use 'list tasks' to see your active tasks."
        )
        return

    task_id = task_id_match.group(1)

    # Verify the task belongs to the user
    user_tasks = task_scheduler.get_user_tasks(user_id)
    if task_id not in user_tasks:
        await update.message.reply_text(
            f"❌ Task '{task_id}' not found or doesn't belong to you.\n\n"
            "Use 'list tasks' to see your active tasks."
        )
        return

    # Cancel the task
    job_queue = context.job_queue
    success = task_scheduler.cancel_task(task_id, job_queue)

    if success:
        await update.message.reply_text(
            f"✅ **Task Cancelled!**\n\n"
            f"🗑️ Task '{task_id}' has been cancelled successfully."
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to cancel task '{task_id}'. Please try again."
        )


async def _handle_auto_detect_scheduler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    user_id: int,
    chat_id: int,
):
    """Auto-detect scheduler type and handle accordingly"""
    text_lower = text.lower()

    # Check for different patterns
    if any(word in text_lower for word in ["after", "in"]) and any(
        word in text_lower for word in ["second", "minute", "hour"]
    ):
        await _handle_create_alarm(update, context, text, user_id, chat_id)
    elif "every" in text_lower:
        await _handle_create_reminder(update, context, text, user_id, chat_id)
    elif any(word in text_lower for word in ["at", "next", "tomorrow"]):
        await _handle_create_notification(update, context, text, user_id, chat_id)
    elif any(word in text_lower for word in ["list", "show", "my tasks"]):
        await _handle_list_tasks(update, context, user_id)
    elif "cancel" in text_lower:
        await _handle_cancel_task(update, context, text, user_id)
    else:
        await update.message.reply_text(
            "🤔 I understand you want to schedule something, but I'm not sure what type. Try:\n\n"
            "**⏰ One-time Alarms:**\n"
            "• 'Set alarm after 20 seconds'\n"
            "• 'Wake me up in 30 minutes'\n\n"
            "**🔁 Recurring Reminders:**\n"
            "• 'Remind me every 25 minutes to stand up'\n"
            "• 'Alert me every hour to drink water'\n\n"
            "**📅 Scheduled Notifications:**\n"
            "• 'Notify me to \"Go to the bank\" next week at 9:00 AM'\n"
            "• 'Schedule meeting reminder tomorrow at 2:30 PM'\n\n"
            "**📋 Task Management:**\n"
            "• 'List my tasks'\n"
            "• 'Cancel task <task_id>'"
        )
