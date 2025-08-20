# src/utils/lock.py
import sys
import fcntl

from src.utils.logging_utils import get_logger  
logger = get_logger(__name__)

def ensure_single_instance(lock_file_path="/tmp/telegram_bot.lock"):
    """
    Ensure only one instance of the bot runs by acquiring an exclusive file lock.

    Args:
        lock_file_path (str): Path to the lock file. Defaults to "/tmp/telegram_bot.lock".

    Returns:
        file: Open file object if the lock is acquired successfully.

    Raises:
        SystemExit: If another instance is already running, exits with status code 1.
    """
    try:
        lock_file = open(lock_file_path, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info(f"Acquired exclusive lock on {lock_file_path}")
        return lock_file
    except OSError:
        logger.error("Another instance of the bot is already running!")
        logger.error(
            f"Check for processes using 'ps aux | grep python' and kill them, or remove {lock_file_path}"
        )
        sys.exit(1)
