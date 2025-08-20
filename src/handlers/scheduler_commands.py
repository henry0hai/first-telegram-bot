# src/handlers/scheduler_commands.py - Scheduler command handlers
from telegram import Update
from telegram.ext import ContextTypes
from src.services.task_scheduler import task_scheduler
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tasks command to list user's scheduled tasks"""
    user_id = update.effective_user.id

    try:
        tasks_text = task_scheduler.list_tasks_text(user_id)
        await update.message.reply_text(tasks_text)

    except Exception as e:
        logger.error(f"Error in tasks command: {e}")
        await update.message.reply_text(
            "❌ Sorry, I encountered an error retrieving your tasks."
        )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command to cancel a specific task"""
    user_id = update.effective_user.id

    # Get task ID from command arguments
    if not context.args:
        await update.message.reply_text(
            "❌ Please specify a task ID to cancel.\n\n"
            "Usage: `/cancel <task_id>`\n"
            "Use `/tasks` to see your active tasks."
        )
        return

    task_id = context.args[0]

    try:
        # Verify the task belongs to the user
        user_tasks = task_scheduler.get_user_tasks(user_id)
        if task_id not in user_tasks:
            await update.message.reply_text(
                f"❌ Task '{task_id}' not found or doesn't belong to you.\n\n"
                "Use `/tasks` to see your active tasks."
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

    except Exception as e:
        logger.error(f"Error in cancel command: {e}")
        await update.message.reply_text(
            f"❌ Sorry, I encountered an error cancelling the task."
        )


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /schedule command - provides scheduler usage help"""
    help_text = """
🕒 **Task Scheduler Help**

The bot can understand natural language scheduling requests:

**⏰ One-time Alarms:**
• "Set alarm after 20 seconds"
• "Wake me up in 30 minutes" 
• "Remind me in 2 hours to call mom"

**🔁 Recurring Reminders:**
• "Remind me every 25 minutes to stand up"
• "Alert me every hour to drink water"
• "Notify me every 30 minutes to check emails"

**📅 Scheduled Notifications:**
• "Notify me to 'Go to the bank' next week at 9:00 AM"
• "Schedule meeting reminder tomorrow at 2:30 PM"
• "Alert me at 8:00 tomorrow"

**📋 Task Management:**
• `/tasks` - List all your scheduled tasks
• `/cancel <task_id>` - Cancel a specific task
• "list my tasks" - Also lists your tasks
• "cancel task <task_id>" - Also cancels tasks

**🔮 Future Features:**
• Weather alerts: "Alert me every hour for weather in Ho Chi Minh City"
• Complex scheduling with webhook automation

Just type your request naturally, and I'll understand what you want to schedule!
"""

    await update.message.reply_text(help_text)
