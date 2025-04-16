"""Formatting helpers for prompts."""

from typing import List

from langchain.output_parsers import PydanticOutputParser

from customer_sentiment_hub.domain.schema import ReviewOutput


def format_reviews_for_prompt(review_texts: List[str]) -> str:
    """
    Format review texts for inclusion in a prompt.
    
    Args:
        review_texts: List of review texts
        
    Returns:
        str: Formatted reviews text
    """
    reviews_input = [f"Review {i+1}: {text}" for i, text in enumerate(review_texts)]
    return "\n\n".join(reviews_input)


def get_format_instructions() -> str:
    """
    Get format instructions for the output parser.
    
    Returns:
        str: Format instructions
    """
    parser = PydanticOutputParser(pydantic_object=ReviewOutput)
    return parser.get_format_instructions()