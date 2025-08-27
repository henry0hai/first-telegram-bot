# src/services/initialization.py
"""
Centralized service initialization to prevent duplicate initialization
"""
import asyncio
from src.services.conversation_history import conversation_service
from src.services.qdrant_conversation_manager import qdrant_conversation_manager
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Global flag to track if services are initialized
_services_initialized = False
_initialization_lock = asyncio.Lock()


async def initialize_services():
    """Initialize all conversation services once"""
    global _services_initialized

    async with _initialization_lock:
        if _services_initialized:
            logger.debug("Services already initialized, skipping")
            return

        try:
            logger.info("Initializing conversation services...")

            # Initialize conversation history service
            await conversation_service.initialize()
            logger.info("Conversation history service initialized successfully")

            # Initialize enhanced Qdrant conversation manager
            await qdrant_conversation_manager.initialize()
            logger.info("Enhanced Qdrant conversation manager initialized successfully")

            _services_initialized = True
            logger.info("All conversation services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize conversation services: {e}")
            raise


def are_services_initialized():
    """Check if services are already initialized"""
    return _services_initialized
