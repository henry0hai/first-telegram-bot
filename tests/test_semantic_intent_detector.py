# tests/test_semantic_intent_detector.py
import pytest
from unittest.mock import patch, MagicMock
import torch

from src.ai.semantic_intent_detector import SemanticIntentDetector
from src.ai.intent_models import IntentType

@pytest.fixture
def mocked_detector():
    """
    Provides a SemanticIntentDetector instance with SentenceTransformer and its utilities mocked,
    preventing actual model loading and computation.
    """
    with patch('src.ai.semantic_intent_detector.SentenceTransformer') as mock_st_class:
        mock_model = MagicMock()
        # all-MiniLM-L6-v2 has 384 dimensions
        mock_model.encode.return_value = torch.zeros(1, 384)
        mock_st_class.return_value = mock_model

        with patch('src.ai.semantic_intent_detector.util.pytorch_cos_sim') as mock_cos_sim:
            detector = SemanticIntentDetector()
            yield detector, mock_cos_sim

def test_initialization_successful(mocked_detector):
    """
    Tests that the SemanticIntentDetector initializes correctly when SentenceTransformer is available.
    """
    detector, _ = mocked_detector
    assert detector.st_available is True
    assert detector.model is not None
    # Ensure embeddings were pre-computed
    assert detector.model.encode.call_count > 0
    # -1 for UNKNOWN
    assert len(detector.intent_embeddings) == len(IntentType) - 1

def test_initialization_failure():
    """
    Tests that the detector handles initialization failure gracefully if SentenceTransformer is missing.
    """
    with patch('src.ai.semantic_intent_detector.SentenceTransformer', side_effect=ImportError("No module named sentence_transformers")):
        detector = SemanticIntentDetector()
        assert detector.st_available is False
        assert detector.model is None
        assert detector.intent_embeddings == {}

def test_calculate_intent_scores_structure(mocked_detector):
    """
    Tests that calculate_intent_scores returns a dictionary with the correct structure and value types.
    """
    detector, mock_cos_sim = mocked_detector
    # Return a dummy similarity
    mock_cos_sim.return_value = torch.tensor([[0.5]])

    scores = detector.calculate_intent_scores("some query")

    assert isinstance(scores, dict)
    assert len(scores) == len(IntentType) - 1
    assert all(isinstance(key, IntentType) for key in scores.keys())
    assert all(isinstance(value, float) for value in scores.values())

@pytest.mark.parametrize(
    "query, expected_intent",
    [
        ("What is my current system status?", IntentType.SYSTEM_INFO),
        ("what is the current weather now?", IntentType.WEATHER),
        ("in this document, what is talking about?", IntentType.RAG_QUERY),
        ("search 10 news for USA today?", IntentType.SEARCH_QUERY),
        ("give me current balance for this month", IntentType.BUDGET_FINANCE),
        ("create simple python script for something", IntentType.DYNAMIC_TOOL),
        ("remind me to buy milk in 20 minutes", IntentType.TASK_SCHEDULER),
    ],
)
def test_intent_detection_scenarios(mocked_detector, query, expected_intent):
    """
    Tests that specific queries are mapped to the correct intent by mocking similarity scores.
    """
    detector, mock_cos_sim = mocked_detector

    # Assume insertion order is preserved for dicts (Python 3.7+)
    intents_order = list(detector.intent_embeddings.keys())
    expected_intent_index = intents_order.index(expected_intent)

    # Create a list of mock return values for the cosine similarity function
    side_effect_list = [torch.tensor([[0.1]])] * len(intents_order)
    side_effect_list[expected_intent_index] = torch.tensor([[0.9]])

    mock_cos_sim.side_effect = side_effect_list

    scores = detector.calculate_intent_scores(query)
    detected_intent = max(scores, key=scores.get)

    assert detected_intent == expected_intent
    assert scores[expected_intent] == pytest.approx(0.9)