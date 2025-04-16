"""Taxonomy definitions for customer sentiment analysis."""

from enum import Enum
from typing import Dict, List, Set, Tuple

# Define constants for clarity
POSITIVE = "Positive"
NEGATIVE = "Negative"
NEUTRAL = "Neutral"


class Sentiment(str, Enum):
    """Valid sentiment values."""
    
    POSITIVE = POSITIVE
    NEGATIVE = NEGATIVE
    NEUTRAL = NEUTRAL


class CategoryType(str, Enum):
    """Main category types."""
    
    PRODUCT_SERVICES = "Product & Services"
    BILLING_PAYMENTS = "Billing & Payments"
    COMMUNICATION = "Communication"
    AGENT_SPECIFIC = "Agent Specific"
    SALES_AFFILIATE = "Sales / Affiliate Related"
    MISCELLANEOUS = "Miscellaneous"


# Define the taxonomy with detailed structure
TAXONOMY = {
    "Sentiments": [s.value for s in Sentiment],
    "Categories": {
        CategoryType.PRODUCT_SERVICES.value: {
            Sentiment.NEGATIVE.value: [
                "Unsettled Debt", "Progress Pace", "Procedure", "Settlement Percentage", 
                "Creditor Correspondence", "Debt Priority", "Settlement Failure", 
                "Summons", "Legal Procedure", "Legal Plan Representation", 
                "Lending", "Unmet Expectations (Services)", "Delayed Cancellation Requests"
            ],
            Sentiment.POSITIVE.value: [
                "Progress Pace", "Procedure", "Settlement Percentage", 
                "Creditor Correspondence", "Debt Priority", "Legal Procedure"
            ],
            Sentiment.NEUTRAL.value: [
                "Progress Pace", "Procedure", "Settlement Percentage",
                "Creditor Correspondence", "Debt Priority", "Legal Procedure",
                "Unsettled Debt"
            ]
        },
        CategoryType.BILLING_PAYMENTS.value: {
            Sentiment.NEGATIVE.value: [
                "Fee Collection", "Additional Funds", "Program Extension", 
                "Draft Amount", "Delayed Refunds", "Unauthorized Drafts", 
                "Fees Amount", "Legal Plan Fees", "Refund Amount"
            ],
            Sentiment.POSITIVE.value: [
                "Fee Collection", "Timely Refunds", "Fees Amount", "Legal Plan Fees"
            ],
            Sentiment.NEUTRAL.value: [
                "Fee Collection", "Fees Amount", "Legal Plan Fees"
            ]
        },
        CategoryType.COMMUNICATION.value: {
            Sentiment.NEGATIVE.value: [
                "Frequency of Calls (High)", "Communication Method", "Delayed Responses", 
                "No Response", "Unmet Expectations", "Difficulty in Reaching Support", 
                "Customer Portal", "Legal Plan Communication", 
                "Unclear Communication / Misleading Information", "Frequency of Calls (Low)", 
                "Request Not Fulfilled"
            ],
            Sentiment.POSITIVE.value: [
                "Clear Communication", "Accurate Information", "Frequency of Calls", 
                "Communication Method", "Timely Responses", "Ease of Access", "Expectations Met"
            ],
            Sentiment.NEUTRAL.value: [
                "Communication Method", "Frequency of Calls", "Customer Portal"
            ]
        },
        CategoryType.AGENT_SPECIFIC.value: {
            Sentiment.NEGATIVE.value: [
                "False Promises", "Knowledge", "Communication & Soft Skills", "Missed Follow-up"
            ],
            Sentiment.POSITIVE.value: [
                "Knowledge", "Communication & Soft Skills"
            ],
            Sentiment.NEUTRAL.value: [
                "Knowledge", "Communication & Soft Skills"
            ]
        },
        CategoryType.SALES_AFFILIATE.value: {
            Sentiment.NEGATIVE.value: [
                "Misrepresentation of Services", "Lack of Follow-up by Affiliate", 
                "Misrepresentation of Legal Plan Services"
            ],
            Sentiment.POSITIVE.value: [
                "Satisfactory Practices"
            ],
            Sentiment.NEUTRAL.value: [
                "Satisfactory Practices"
            ]
        },
        CategoryType.MISCELLANEOUS.value: {
            Sentiment.NEGATIVE.value: [
                "Creditor Calls", "Credit Score", "Other", "Scam / Fraud Allegations", "Judgement"
            ],
            Sentiment.POSITIVE.value: [
                "Credit Score"
            ],
            Sentiment.NEUTRAL.value: [
                "Credit Score", "Other"
            ]
        }
    }
}


def get_valid_categories() -> Set[str]:
    """
    Get a set of valid category names.
    
    Returns:
        Set[str]: Set of valid category names
    """
    return set(TAXONOMY["Categories"].keys())


def get_valid_subcategories() -> Dict[str, Set[str]]:
    """
    Get a dictionary mapping categories to their valid subcategories.
    
    Returns:
        Dict[str, Set[str]]: Dictionary mapping categories to their subcategories
    """
    result = {}
    for category, sentiment_subcats in TAXONOMY["Categories"].items():
        result[category] = set()
        for sentiment in Sentiment:
            result[category].update(sentiment_subcats[sentiment.value])
    return result


def generate_taxonomy_string() -> str:
    """
    Generate a formatted string representation of the taxonomy for use in prompts.
    
    Returns:
        str: Formatted taxonomy string
    """
    taxonomy_str = """
For review classification, use ONLY the following taxonomy:

MAIN CATEGORIES:
"""
    
    for category in TAXONOMY["Categories"]:
        taxonomy_str += f"- {category}\n"
    
    taxonomy_str += "\nFOR EACH MAIN CATEGORY, USE ONLY THESE SUBCATEGORIES:\n"
    
    for category, sentiment_subcats in TAXONOMY["Categories"].items():
        taxonomy_str += f"\n{category}:\n"
        
        for sentiment in Sentiment:
            taxonomy_str += f"  {sentiment.value} sentiment subcategories:\n"
            for subcat in sentiment_subcats[sentiment.value]:
                taxonomy_str += f"  - {subcat}\n"
            taxonomy_str += "\n"
    
    return taxonomy_str