"""
Taxonomy definitions for customer sentiment analysis.

This module defines the hierarchical structure of categories, subcategories,
and sentiment classifications used for analyzing customer reviews.
"""

from enum import Enum
from typing import Dict, FrozenSet
from functools import lru_cache

# Define constants for clarity and maintainability
POSITIVE = "Positive"
NEGATIVE = "Negative"
NEUTRAL = "Neutral"


class Sentiment(str, Enum):
    """
    Valid sentiment values for customer reviews.
    
    These represent the emotional tone detected in customer feedback:
    - POSITIVE: Indicates customer satisfaction or approval
    - NEGATIVE: Indicates customer dissatisfaction or disapproval
    - NEUTRAL: Indicates neither clear satisfaction nor dissatisfaction
    """
    
    POSITIVE = POSITIVE
    NEGATIVE = NEGATIVE
    NEUTRAL = NEUTRAL


class CategoryType(str, Enum):
    """
    Main category types for customer review classification.
    
    These top-level categories organize feedback into major business areas:
    - PRODUCT_SERVICES: Issues related to the core product and service offerings
    - BILLING_PAYMENTS: Financial and payment-related concerns
    - COMMUNICATION: Interactions and information exchange with customers
    - AGENT_SPECIFIC: Issues related to specific customer service agents
    - SALES_AFFILIATE: Issues related to sales practices or affiliate programs
    - MISCELLANEOUS: Other issues that don't fit in primary categories
    """
    
    PRODUCT_SERVICES = "Product & Services"
    BILLING_PAYMENTS = "Billing & Payments"
    COMMUNICATION = "Communication"
    AGENT_SPECIFIC = "Agent Specific"
    SALES_AFFILIATE = "Sales / Affiliate Related"
    MISCELLANEOUS = "Miscellaneous"


# Using immutable frozensets for better performance in lookups
TAXONOMY = {
    "Sentiments": frozenset(s.value for s in Sentiment),
    "Categories": {
        CategoryType.PRODUCT_SERVICES.value: {
            Sentiment.NEGATIVE.value: frozenset([
                "Unsettled Debt", "Progress Pace", "Procedure", "Settlement Percentage", 
                "Creditor Correspondence", "Debt Priority", "Settlement Failure", 
                "Summons", "Legal Procedure", "Legal Plan Representation", 
                "Lending", "Unmet Expectations (Services)", "Delayed Cancellation Requests"
            ]),
            Sentiment.POSITIVE.value: frozenset([
                "Progress Pace", "Procedure", "Settlement Percentage", 
                "Creditor Correspondence", "Debt Priority", "Legal Procedure"
            ]),
            Sentiment.NEUTRAL.value: frozenset([
                "Progress Pace", "Procedure", "Settlement Percentage",
                "Creditor Correspondence", "Debt Priority", "Legal Procedure",
                "Unsettled Debt"
            ])
        },
        CategoryType.BILLING_PAYMENTS.value: {
            Sentiment.NEGATIVE.value: frozenset([
                "Fee Collection", "Additional Funds", "Program Extension", 
                "Draft Amount", "Delayed Refunds", "Unauthorized Drafts", 
                "Fees Amount", "Legal Plan Fees", "Refund Amount"
            ]),
            Sentiment.POSITIVE.value: frozenset([
                "Fee Collection", "Timely Refunds", "Fees Amount", "Legal Plan Fees"
            ]),
            Sentiment.NEUTRAL.value: frozenset([
                "Fee Collection", "Fees Amount", "Legal Plan Fees"
            ])
        },
        CategoryType.COMMUNICATION.value: {
            Sentiment.NEGATIVE.value: frozenset([
                "Frequency of Calls (High)", "Communication Method", "Delayed Responses", 
                "No Response", "Unmet Expectations", "Difficulty in Reaching Support", 
                "Customer Portal", "Legal Plan Communication", 
                "Unclear Communication / Misleading Information", "Frequency of Calls (Low)", 
                "Request Not Fulfilled"
            ]),
            Sentiment.POSITIVE.value: frozenset([
                "Clear Communication", "Accurate Information", "Frequency of Calls", 
                "Communication Method", "Timely Responses", "Ease of Access", "Expectations Met"
            ]),
            Sentiment.NEUTRAL.value: frozenset([
                "Communication Method", "Frequency of Calls", "Customer Portal"
            ])
        },
        CategoryType.AGENT_SPECIFIC.value: {
            Sentiment.NEGATIVE.value: frozenset([
                "False Promises", "Knowledge", "Communication & Soft Skills", "Missed Follow-up"
            ]),
            Sentiment.POSITIVE.value: frozenset([
                "Knowledge", "Communication & Soft Skills"
            ]),
            Sentiment.NEUTRAL.value: frozenset([
                "Knowledge", "Communication & Soft Skills"
            ])
        },
        CategoryType.SALES_AFFILIATE.value: {
            Sentiment.NEGATIVE.value: frozenset([
                "Misrepresentation of Services", "Lack of Follow-up by Affiliate", 
                "Misrepresentation of Legal Plan Services"
            ]),
            Sentiment.POSITIVE.value: frozenset([
                "Satisfactory Practices"
            ]),
            Sentiment.NEUTRAL.value: frozenset([
                "Satisfactory Practices"
            ])
        },
        CategoryType.MISCELLANEOUS.value: {
            Sentiment.NEGATIVE.value: frozenset([
                "Creditor Calls", "Credit Score", "Other", "Scam / Fraud Allegations", "Judgement"
            ]),
            Sentiment.POSITIVE.value: frozenset([
                "Credit Score"
            ]),
            Sentiment.NEUTRAL.value: frozenset([
                "Credit Score", "Other"
            ])
        }
    }
}

# Build lookup dictionaries at module load time for faster access
_SUBCATEGORY_TO_CATEGORY = {}
for category, sentiment_subcats in TAXONOMY["Categories"].items():
    for sentiment, subcategories in sentiment_subcats.items():
        for subcategory in subcategories:
            _SUBCATEGORY_TO_CATEGORY[subcategory] = category

# Cache these frequently used functions to improve performance
@lru_cache(maxsize=1)
def get_valid_categories() -> FrozenSet[str]:
    """
    Get a frozenset of valid category names.
    
    Returns:
        FrozenSet[str]: Immutable set of valid category names
        
    Performance:
        O(1) - Uses cached result after first call
    """
    return frozenset(TAXONOMY["Categories"].keys())


@lru_cache(maxsize=1)
def get_valid_subcategories() -> Dict[str, FrozenSet[str]]:
    """
    Get a dictionary mapping categories to their valid subcategories.
    
    Returns:
        Dict[str, FrozenSet[str]]: Dictionary mapping categories to their subcategories
        
    Performance:
        O(1) - Uses cached result after first call
    """
    result = {}
    for category, sentiment_subcats in TAXONOMY["Categories"].items():
        combined = set()
        for sentiment in Sentiment:
            combined.update(sentiment_subcats[sentiment.value])
        result[category] = frozenset(combined)
    return result


def get_category_for_subcategory(subcategory: str) -> str:
    """
    Get the parent category for a given subcategory.
    
    Args:
        subcategory: The subcategory to look up
        
    Returns:
        str: The parent category name, or "Miscellaneous" if not found
        
    Performance:
        O(1) - Uses precomputed lookup dictionary
    """
    return _SUBCATEGORY_TO_CATEGORY.get(subcategory, CategoryType.MISCELLANEOUS.value)


def is_valid_subcategory_for_category(category: str, subcategory: str) -> bool:
    """
    Check if a subcategory is valid for a given category.
    
    Args:
        category: The category name to check
        subcategory: The subcategory name to check
        
    Returns:
        bool: True if the subcategory belongs to the category
        
    Performance:
        O(1) - Uses frozenset lookups
    """
    subcats = get_valid_subcategories().get(category)
    return subcats is not None and subcategory in subcats


@lru_cache(maxsize=1)
def generate_taxonomy_string() -> str:
    """
    Generate a formatted string representation of the taxonomy for use in prompts.
    
    This creates a human-readable format of the taxonomy that can be included
    in prompts to language models for consistent classification.
    
    Returns:
        str: Formatted taxonomy string
        
    Performance:
        O(1) - Uses cached result after first call
    """
    taxonomy_parts = [
        "For review classification, use ONLY the following taxonomy:",
        "",
        "MAIN CATEGORIES:"
    ]
    
    # Add main categories
    for category in TAXONOMY["Categories"]:
        taxonomy_parts.append(f"- {category}")
    
    taxonomy_parts.append("\nFOR EACH MAIN CATEGORY, USE ONLY THESE SUBCATEGORIES:\n")
    
    # Add subcategories by sentiment
    for category, sentiment_subcats in TAXONOMY["Categories"].items():
        taxonomy_parts.append(f"\n{category}:")
        
        for sentiment in Sentiment:
            taxonomy_parts.append(f"  {sentiment.value} sentiment subcategories:")
            for subcat in sorted(sentiment_subcats[sentiment.value]):
                taxonomy_parts.append(f"  - {subcat}")
            taxonomy_parts.append("")
    
    # Join all parts with newlines
    return "\n".join(taxonomy_parts)