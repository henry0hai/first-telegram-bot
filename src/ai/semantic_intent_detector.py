# src/ai/semantic_intent_detector.py
from typing import Dict, List
from sentence_transformers import SentenceTransformer, util
from src.ai.intent_models import IntentType
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

class SemanticIntentDetector:
    """
    Detects intent using semantic similarity with sentence-transformers.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            self.model = SentenceTransformer(model_name)
            self.st_available = True
            logger.info(f"SentenceTransformer model '{model_name}' loaded successfully.")
        except Exception as e:
            self.model = None
            self.st_available = False
            logger.warning(
                f"SentenceTransformer model not available. Intent detection will fall back to keywords. Error: {e}"
            )
            logger.warning("For best results, run: pip install sentence-transformers")

        self.intent_descriptions = {
            IntentType.RAG_QUERY: [
                "what is this document about?",
                "summarize this file",
                "explain the contents of this document",
                "according to the uploaded file, what is...",
                "tell me about the model context protocol",
            ],
            IntentType.SEARCH_QUERY: [
                "search for the latest news on space exploration",
                "find information about quantum computing",
                "look up recent developments in AI",
                "what's new with Large Language Models?",
            ],
            IntentType.SYSTEM_INFO: [
                "what is my current system status?",
                "show me the hardware specifications",
                "how much memory is being used?",
                "check the server's CPU and disk usage",
            ],
            IntentType.DYNAMIC_TOOL: [
                "create a python script to solve a math problem",
                "write a bash script to automate a task",
                "generate code to process a file",
                "make a tool that fetches data from an API",
                "create a simple python app for...",
            ],
            IntentType.WEATHER: [
                "what is the current weather in London?",
                "is it going to rain tomorrow in New York?",
                "get the weather forecast for this week",
                "how hot will it be today?",
            ],
            IntentType.BUDGET_FINANCE: [
                "what is my current budget balance for this month?",
                "how much have I spent on groceries?",
                "add a new expense of $50 for dinner",
                "show me a summary of my finances",
            ],
            IntentType.EMAIL_COMMUNICATION: [
                "send an email to john doe about the project update",
                "check my inbox for new messages",
                "compose a reply to the last email",
                "forward this message to my team",
            ],
            IntentType.TRANSLATION_LANGUAGE: [
                "translate 'hello world' to Spanish",
                "what does this sentence mean in English?",
                "convert this text to French",
                "provide a multilingual translation of this document",
            ],
            IntentType.TASK_SCHEDULER: [
                "remind me to drink water in 20 minutes",
                "set an alarm for 7 AM tomorrow",
                "create a recurring reminder for my weekly meeting",
                "alert me every 2 hours to take a break",
                "list my scheduled tasks",
            ],
        }

        self.intent_embeddings = self._precompute_intent_embeddings()

    def _precompute_intent_embeddings(self) -> Dict[IntentType, List[object]]:
        """Pre-computes embeddings for all intent descriptions for faster matching."""
        if not self.st_available:
            return {}

        logger.info("Pre-computing intent description embeddings...")
        embeddings = {}
        for intent, descriptions in self.intent_descriptions.items():
            embeddings[intent] = self.model.encode(descriptions, convert_to_tensor=True)
        logger.info("Intent embeddings computed.")
        return embeddings

    def calculate_intent_scores(self, text: str) -> Dict[IntentType, float]:
        """
        Calculates similarity scores for each intent based on the user's query.

        Args:
            text: The user's input query.

        Returns:
            A dictionary mapping each IntentType to a similarity score (float).
        """
        if not self.st_available:
            return {intent: 0.0 for intent in self.intent_descriptions.keys()}

        query_embedding = self.model.encode(text, convert_to_tensor=True)
        scores = {}

        for intent, description_embeddings in self.intent_embeddings.items():
            similarities = util.pytorch_cos_sim(query_embedding, description_embeddings)
            max_similarity = similarities.max().item()
            scores[intent] = max_similarity

        return scores


