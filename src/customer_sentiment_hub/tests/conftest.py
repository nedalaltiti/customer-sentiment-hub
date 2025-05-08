"""Test configuration and fixtures."""

import json
import os
from pathlib import Path
from typing import Dict, List

import pytest

from customer_sentiment_hub.config.settings import (
    AppSettings, GeminiSettings, GoogleCloudSettings, ProcessingSettings
)
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.services.gemini_service import GeminiService


@pytest.fixture
def test_settings() -> AppSettings:
    """Create test settings."""
    return AppSettings(
        debug=True,
        log_level="DEBUG",
        gemini=GeminiSettings(
            model_name="gemini-2.0-flash-001",
            temperature=0.0,
            max_output_tokens=1024
        ),
        google_cloud=GoogleCloudSettings(
            project_id="test-project",
            location="us-central1"
        ),
        processing=ProcessingSettings(
            batch_size=2,
            confidence_threshold=0.3,
            max_labels_per_review=3
        )
    )


@pytest.fixture
def validation_service() -> ValidationService:
    """Create a validation service."""
    return ValidationService()


@pytest.fixture
def sample_reviews() -> List[str]:
    """Sample review texts for testing."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "reviews.json", "r") as f:
        data = json.load(f)
    return [review["text"] for review in data["reviews"]]


@pytest.fixture
def sample_response() -> Dict:
    """Sample LLM response for testing."""
    fixtures_dir = Path(__file__).parent / "fixtures"
    with open(fixtures_dir / "responses.json", "r") as f:
        return json.load(f)


@pytest.fixture
def mock_llm_service(sample_response):
    """Mock LLM service that returns a predefined response."""
    from customer_sentiment_hub.services.llm_service import LLMService
    from customer_sentiment_hub.utils.result import Success
    
    class MockLLMService(LLMService):
        async def analyze_reviews(self, review_texts):
            return Success(sample_response)
    
    return MockLLMService()