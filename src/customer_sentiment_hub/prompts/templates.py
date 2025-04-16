"""Prompt templates for LLM services."""

from langchain.prompts import ChatPromptTemplate

from customer_sentiment_hub.domain.taxonomy import generate_taxonomy_string
from customer_sentiment_hub.prompts.formatters import get_format_instructions


def create_review_analysis_prompt() -> ChatPromptTemplate:
    """
    Create a prompt template for review analysis.
    
    Returns:
        ChatPromptTemplate: The prompt template
    """
    template = """You are an expert in customer feedback analysis for debt settlement services.
            
Your task is to analyze customer reviews and classify them according to the following taxonomy:

{taxonomy}

IMPORTANT RULES:
1. Sentiment must be ONLY "Positive", "Negative", or "Neutral" - these are NOT categories
2. Main categories are like "Product & Services", "Billing & Payments", etc.
3. Each review can have multiple labels (category, subcategory, sentiment triplets)
4. You MUST ONLY use the exact categories and subcategories listed above
5. DO NOT use "Positive", "Negative", or "Neutral" as categories - they are sentiments only
6. Determine sentiment SPECIFICALLY for each category/subcategory pair, NOT for the overall review
7. Use "Neutral" when the sentiment is neither clearly positive nor negative

For each review, follow this process:
1. First identify all main categories mentioned in the review (e.g., "Product & Services", "Billing & Payments")
2. For each identified category, select the most appropriate subcategory
3. For each category/subcategory pair, determine the sentiment (Positive, Negative, or Neutral) SPECIFIC to that topic
4. Create a triplet of (category, subcategory, sentiment)

IMPORTANT: Different parts of the review may have different sentiments. For example, a customer may be 
positive about communication but negative about fees. Each category should have its own sentiment assessment.

Reviews to classify:
{reviews}

{format_instructions}
"""
    
    return ChatPromptTemplate.from_template(template)


def get_populated_prompt(reviews: str) -> ChatPromptTemplate:
    """
    Get a populated prompt with reviews and taxonomy.
    
    Args:
        reviews: Review texts formatted for inclusion in the prompt
        
    Returns:
        ChatPromptTemplate: The populated prompt template
    """
    template = create_review_analysis_prompt()
    
    # Get the taxonomy string
    taxonomy_string = generate_taxonomy_string()
    
    # Get format instructions
    format_instructions = get_format_instructions()
    
    return template.partial(
        taxonomy=taxonomy_string,
        format_instructions=format_instructions,
    )