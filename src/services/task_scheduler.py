# src/services/task_scheduler.py - Advanced task scheduling service
import re
import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Callable
from telegram.ext import CallbackContext
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Types of scheduler tasks"""

    ALARM = "alarm"  # One-time notification after delay
    REMINDER = "reminder"  # Recurring reminders
    NOTIFICATION = "notification"  # Scheduled notification at specific time
    WEBHOOK_TASK = "webhook_task"  # Future: webhook-based tasks


@dataclass
class ScheduledTask:
    """Represents a scheduled task"""

    task_id: str
    task_type: TaskType
    user_id: int
    chat_id: int
    message: str
    scheduled_time: datetime.datetime
    interval: Optional[int] = None  # For recurring tasks (in seconds)
    webhook_data: Optional[Dict[str, Any]] = None  # For future webhook tasks
    is_active: bool = True


class TaskScheduler:
    """Advanced task scheduler for MCP bot"""

    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.time_patterns = {
            "seconds": [
                r"(?:after|in)\s+(\d+)\s*(?:second|sec|s)",
            ],
            "minutes": [
                r"(?:after|in)\s+(\d+)\s*(?:minute|min|m)",
            ],
            "hours": [r"(?:after|in)\s+(\d+)\s*(?:hour|hr|h)"],
            "days": [r"(?:after|in)\s+(\d+)\s*(?:day|d)"],
        }

        self.recurring_patterns = [
            r"every\s+(\d+)\s*(?:second|sec|s)",
            r"every\s+(\d+)\s*(?:minute|min|m)",
            r"every\s+(\d+)\s*(?:hour|hr|h)",
            r"every\s+(\d+)\s*(?:day|d)",
            # Add patterns for "every hour", "every minute", etc. without numbers
            r"every\s+hour",
            r"every\s+minute",
            r"every\s+second",
            r"every\s+day",
        ]

        self.absolute_time_patterns = [
            r"at\s+(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)?",
            r"on\s+(\w+)\s+at\s+(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)?",
            r"(?:next|this)\s+(\w+)\s+at\s+(\d{1,2}):(\d{2})\s*(?:AM|PM|am|pm)?",
        ]

    def parse_time_delay(self, text: str) -> Optional[int]:
        """Parse time delay from text and return seconds"""
        text_lower = text.lower()

        # Check for relative time patterns
        for unit, patterns in self.time_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    value = int(match.group(1))
                    if unit == "seconds":
                        return value
                    elif unit == "minutes":
                        return value * 60
                    elif unit == "hours":
                        return value * 3600
                    elif unit == "days":
                        return value * 86400

        return None

    def parse_recurring_interval(self, text: str) -> Optional[int]:
        """Parse recurring interval from text and return seconds"""
        text_lower = text.lower()

        # Check for numbered patterns first (e.g., "every 25 minutes")
        numbered_patterns = [
            (r"every\s+(\d+)\s*(?:second|sec|s)", 1),
            (r"every\s+(\d+)\s*(?:minute|min|m)", 60),
            (r"every\s+(\d+)\s*(?:hour|hr|h)", 3600),
            (r"every\s+(\d+)\s*(?:day|d)", 86400),
        ]

        for pattern, multiplier in numbered_patterns:
            match = re.search(pattern, text_lower)
            if match:
                value = int(match.group(1))
                return value * multiplier

        # Check for single unit patterns (e.g., "every hour", "every minute")
        single_patterns = [
            (r"every\s+second", 1),
            (r"every\s+minute", 60),
            (r"every\s+hour", 3600),
            (r"every\s+day", 86400),
        ]

        for pattern, seconds in single_patterns:
            if re.search(pattern, text_lower):
                return seconds

        return None

    def parse_absolute_time(self, text: str) -> Optional[datetime.datetime]:
        """Parse absolute time from text"""
        text_lower = text.lower()
        now = datetime.datetime.now()

        # Simple time pattern (today)
        time_match = re.search(r"at\s+(\d{1,2}):(\d{2})\s*(am|pm)?", text_lower)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            am_pm = time_match.group(3)

            if am_pm:
                if am_pm == "pm" and hour != 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0

            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += datetime.timedelta(days=1)

            return target_time

        # Next week pattern
        next_week_match = re.search(
            r"next\s+week\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)?", text_lower
        )
        if next_week_match:
            hour = int(next_week_match.group(1))
            minute = int(next_week_match.group(2))
            am_pm = next_week_match.group(3)

            if am_pm:
                if am_pm == "pm" and hour != 12:
                    hour += 12
                elif am_pm == "am" and hour == 12:
                    hour = 0

            # Find next Monday (start of next week)
            days_ahead = 7 - now.weekday()  # Monday is 0
            if days_ahead == 0:  # Today is Monday
                days_ahead = 7

            target_date = now + datetime.timedelta(days=days_ahead)
            target_time = target_date.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

            return target_time

        return None

    def extract_task_message(self, text: str) -> str:
        """Extract the custom message from the task text"""
        # Look for quoted messages
        quoted_match = re.search(r'["\']([^"\']+)["\']', text)
        if quoted_match:
            return quoted_match.group(1)

        # Look for "to" or "about" patterns
        to_match = re.search(
            r"(?:to|about)\s+(.+?)(?:\s+(?:after|every|at|on|next)|\s*$)",
            text,
            re.IGNORECASE,
        )
        if to_match:
            return to_match.group(1).strip()

        # Look for "remind me" patterns
        remind_match = re.search(
            r"remind\s+me\s+(.+?)(?:\s+every|\s*$)", text, re.IGNORECASE
        )
        if remind_match:
            return f"Reminder: {remind_match.group(1).strip()}"

        return "Scheduled notification"

    def _detect_scheduler_type(self, text_lower: str) -> str:
        """Detect the type of scheduler request"""
        # Check for cancel/list operations first (highest priority)
        if any(word in text_lower for word in ["cancel", "remove", "delete", "stop"]):
            return "cancel"
        elif any(word in text_lower for word in ["list", "show", "my tasks", "tasks"]):
            return "list"
        # Check for recurring patterns (high priority)
        elif any(
            word in text_lower for word in ["every", "remind", "recurring", "repeat"]
        ):
            return "reminder"
        # Check for alarm patterns (specific patterns including "alarm", "wake", "after", "in X time")
        elif any(word in text_lower for word in ["alarm", "wake me"]) or re.search(
            r"\bafter\s+\d+|\bin\s+\d+\s+(second|minute|hour)", text_lower
        ):
            return "alarm"
        # Check for absolute time patterns (notification)
        elif any(
            word in text_lower
            for word in ["at", "on", "next week", "tomorrow", "schedule"]
        ):
            return "notification"
        else:
            return "unknown"

    def create_alarm(
        self, user_id: int, chat_id: int, text: str, job_queue
    ) -> Optional[str]:
        """Create a one-time alarm"""
        delay = self.parse_time_delay(text)
        if not delay:
            return None

        message = self.extract_task_message(text)
        task_id = f"alarm_{user_id}_{datetime.datetime.now().timestamp()}"

        scheduled_time = datetime.datetime.now() + datetime.timedelta(seconds=delay)

        task = ScheduledTask(
            task_id=task_id,
            task_type=TaskType.ALARM,
            user_id=user_id,
            chat_id=chat_id,
            message=message,
            scheduled_time=scheduled_time,
        )

        self.tasks[task_id] = task

        # Schedule the job
        job_queue.run_once(
            callback=self._create_notification_callback(task_id),
            when=delay,
            name=task_id,
        )

        logger.info(f"Created alarm: {task_id} for user {user_id}")
        return task_id

    def create_reminder(
        self, user_id: int, chat_id: int, text: str, job_queue
    ) -> Optional[str]:
        """Create a recurring reminder"""
        interval = self.parse_recurring_interval(text)
        if not interval:
            return None

        message = self.extract_task_message(text)
        task_id = f"reminder_{user_id}_{datetime.datetime.now().timestamp()}"

        scheduled_time = datetime.datetime.now() + datetime.timedelta(seconds=interval)

        task = ScheduledTask(
            task_id=task_id,
            task_type=TaskType.REMINDER,
            user_id=user_id,
            chat_id=chat_id,
            message=message,
            scheduled_time=scheduled_time,
            interval=interval,
        )

        self.tasks[task_id] = task

        # Schedule the recurring job
        job_queue.run_repeating(
            callback=self._create_notification_callback(task_id),
            interval=interval,
            first=interval,
            name=task_id,
        )

        logger.info(f"Created reminder: {task_id} for user {user_id}")
        return task_id

    def create_notification(
        self, user_id: int, chat_id: int, text: str, job_queue
    ) -> Optional[str]:
        """Create a scheduled notification"""
        scheduled_time = self.parse_absolute_time(text)
        if not scheduled_time:
            return None

        message = self.extract_task_message(text)
        task_id = f"notification_{user_id}_{datetime.datetime.now().timestamp()}"

        task = ScheduledTask(
            task_id=task_id,
            task_type=TaskType.NOTIFICATION,
            user_id=user_id,
            chat_id=chat_id,
            message=message,
            scheduled_time=scheduled_time,
        )

        self.tasks[task_id] = task

        # Calculate delay
        delay = (scheduled_time - datetime.datetime.now()).total_seconds()

        if delay > 0:
            job_queue.run_once(
                callback=self._create_notification_callback(task_id),
                when=delay,
                name=task_id,
            )

            logger.info(f"Created notification: {task_id} for user {user_id}")
            return task_id

        return None

    def _create_notification_callback(self, task_id: str):
        """Create an async-compatible callback for job queue"""

        async def callback(context: CallbackContext):
            await self._send_notification(context, task_id)

        return callback

    async def _send_notification(self, context: CallbackContext, task_id: str):
        """Send notification to user"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        try:
            # Send message to user
            await context.bot.send_message(
                chat_id=task.chat_id, text=f"🔔 {task.message}"
            )

            # Remove non-recurring tasks
            if task.task_type != TaskType.REMINDER:
                del self.tasks[task_id]

            logger.info(f"Sent notification for task: {task_id}")

        except Exception as e:
            logger.error(f"Failed to send notification for task {task_id}: {e}")

    def cancel_task(self, task_id: str, job_queue) -> bool:
        """Cancel a scheduled task"""
        if task_id not in self.tasks:
            return False

        try:
            # Remove from job queue
            current_jobs = job_queue.get_jobs_by_name(task_id)
            for job in current_jobs:
                job.schedule_removal()

            # Remove from tasks
            del self.tasks[task_id]

            logger.info(f"Cancelled task: {task_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

    def get_user_tasks(self, user_id: int) -> Dict[str, ScheduledTask]:
        """Get all tasks for a specific user"""
        return {
            task_id: task
            for task_id, task in self.tasks.items()
            if task.user_id == user_id and task.is_active
        }

    def list_tasks_text(self, user_id: int) -> str:
        """Generate text listing all tasks for a user"""
        user_tasks = self.get_user_tasks(user_id)

        if not user_tasks:
            return "📋 You have no scheduled tasks."

        text = "📋 **Your Scheduled Tasks:**\n\n"

        for task_id, task in user_tasks.items():
            task_type_emoji = {
                TaskType.ALARM: "⏰",
                TaskType.REMINDER: "🔁",
                TaskType.NOTIFICATION: "📅",
            }

            emoji = task_type_emoji.get(task.task_type, "🔔")
            type_name = task.task_type.value.title()

            text += f"{emoji} **{type_name}**\n"
            text += f"   Message: {task.message}\n"
            text += f"   Time: {task.scheduled_time.strftime('%Y-%m-%d %H:%M')}\n"

            if task.interval:
                if task.interval < 60:
                    text += f"   Interval: {task.interval} seconds\n"
                elif task.interval < 3600:
                    minutes = task.interval // 60
                    seconds = task.interval % 60
                    if seconds > 0:
                        text += f"   Interval: {minutes} minutes {seconds} seconds\n"
                    else:
                        text += f"   Interval: {minutes} minutes\n"
                else:
                    hours = task.interval // 3600
                    minutes = (task.interval % 3600) // 60
                    if minutes > 0:
                        text += f"   Interval: {hours} hours {minutes} minutes\n"
                    else:
                        text += f"   Interval: {hours} hours\n"

            text += f"   ID: `{task_id}`\n\n"

        text += "💡 Use 'cancel task <ID>' to remove a task."
        return text


# Global scheduler instance
task_scheduler = TaskScheduler()
