"""Gemini LLM service implementation."""

import logging
from typing import Dict, List, Optional

from google.cloud import aiplatform
from langchain_google_vertexai import ChatVertexAI
from langchain.output_parsers import PydanticOutputParser

from customer_sentiment_hub.config.settings import GeminiSettings, GoogleCloudSettings
from customer_sentiment_hub.domain.schema import ReviewOutput
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.prompts.formatters import format_reviews_for_prompt
from customer_sentiment_hub.prompts.templates import get_populated_prompt
from customer_sentiment_hub.services.llm_service import LLMService
from customer_sentiment_hub.utils.result import Result, Success, Error

logger = logging.getLogger(__name__)


class GeminiService(LLMService):
    """Service for interacting with Google's Gemini models."""
    
    def __init__(
        self,
        gemini_settings: GeminiSettings,
        google_settings: GoogleCloudSettings,
        validation_service: Optional[ValidationService] = None,
    ):
        """
        Initialize the Gemini service.
        
        Args:
            gemini_settings: Settings for the Gemini model
            google_settings: Google Cloud settings
            validation_service: Validation service for output validation
        """
        self.settings = gemini_settings
        self.google_settings = google_settings
        self.validation_service = validation_service or ValidationService()
        
        # Initialize Vertex AI if project_id is provided
        if google_settings.project_id:
            aiplatform.init(
                project=google_settings.project_id,
                location=google_settings.location
            )
        
        # Initialize the LLM
        self.llm = ChatVertexAI(
            model_name=gemini_settings.model_name,
            temperature=gemini_settings.temperature,
            max_output_tokens=gemini_settings.max_output_tokens
        )
        
        # Initialize the parser
        self.parser = PydanticOutputParser(pydantic_object=ReviewOutput)
        
        logger.info(
            f"Initialized Gemini service with model {gemini_settings.model_name}"
        )
    
    async def test_connection(self) -> bool:
        """
        Test connection to Gemini API.
        
        Returns:
            bool: True if connection is successful, raises an exception otherwise
        """
        try:
            # Simple test to check if Gemini API is accessible
            # Use a minimal prompt that requires minimal tokens and processing
            test_response = self.llm.invoke("Hello, are you available?")
            
            # If we get a response, connection is successful
            if test_response and hasattr(test_response, 'content'):
                logger.info("Gemini API connection test successful")
                return True
            else:
                logger.error("Gemini API connection test failed: No response content")
                raise ConnectionError("No response content from Gemini API")
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {str(e)}")
            raise
    
    async def analyze_reviews(self, review_texts: List[str]) -> Result[Dict]:
        """
        Analyze a batch of review texts.
        
        Args:
            review_texts: List of review texts to analyze
            
        Returns:
            Result containing analysis results or error
        """
        logger.info(f"Analyzing {len(review_texts)} reviews with Gemini")
        
        try:
            # Format the reviews for the prompt
            reviews_text = format_reviews_for_prompt(review_texts)
            
            # Get the populated prompt
            prompt = get_populated_prompt(reviews_text)
            
            # Format the prompt
            formatted_prompt = prompt.format(reviews=reviews_text)
            
            # Send request to Gemini
            response = self.llm.invoke(formatted_prompt)
            response_text = response.content
            
            logger.debug(f"Received response of length {len(response_text)}")
            
            # Parse the output
            try:
                # Try to parse with Pydantic
                output = self.parser.parse(response_text)
                
                # Update review_ids to match input order
                for i, review in enumerate(output.reviews):
                    review.review_id = str(1000 + i)
                    review.text = review_texts[i]
                
                # Convert to dict
                results = output.model_dump()
                
                # Clean and validate the results
                cleaned_results = self._clean_results(results)
                
                logger.info(f"Successfully processed {len(review_texts)} reviews")
                return Success(cleaned_results)
                
            except Exception as e:
                logger.warning(f"Error parsing response: {str(e)}")
                
                try:
                    import json
                    import re
                    
                    # Try to find JSON using a regex pattern
                    json_pattern = r'```json\s*([\s\S]*?)\s*```'
                    match = re.search(json_pattern, response_text)
                    if match:
                        json_str = match.group(1)
                        parsed_json = json.loads(json_str)
                    else:
                        # Try to find JSON using braces
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            json_str = response_text[json_start:json_end]
                            parsed_json = json.loads(json_str)
                        else:
                            raise ValueError("Could not extract JSON from response")
                    
                   
                    if "reviews" not in parsed_json:
                        restructured = {"reviews": []}
                        
                        # Handle case where we just got a single review
                        if "labels" in parsed_json:
                            parsed_json["review_id"] = "1000"
                            parsed_json["text"] = review_texts[0]
                            restructured["reviews"].append(parsed_json)
                        elif isinstance(parsed_json, list) and len(parsed_json) > 0:
                            # Handle case where we got a list of reviews
                            for i, review in enumerate(parsed_json):
                                if i < len(review_texts):
                                    review["review_id"] = str(1000 + i)
                                    review["text"] = review_texts[i]
                                    restructured["reviews"].append(review)
                        
                        parsed_json = restructured
                    
                    # Clean and validate the results
                    cleaned_results = self._clean_results(parsed_json)
                    
                    logger.info(
                        f"Processed {len(review_texts)} reviews with fallback JSON parsing"
                    )
                    return Success(cleaned_results)
                    
                except Exception as json_error:
                    error_msg = f"Failed to parse response: {str(json_error)}"
                    logger.error(error_msg)
                    return Error(error_msg)
        
        except Exception as e:
            error_msg = f"Error analyzing reviews: {str(e)}"
            logger.error(error_msg)
            return Error(error_msg)
    

    def _ensure_at_least_one_label(self, review: Dict) -> Dict:
        """Guarantee each review has ≥1 label; inject Misc/Other if empty."""
        if not review.get("labels"):
            text = review.get("text", "")
            review["labels"] = [{
                "category": "Miscellaneous",
                "subcategory": "Other"
            }]
        return review

    def _clean_results(self, results: Dict) -> Dict:
        """
        Clean and validate the results.
        
        Args:
            results: Raw results to clean
            
        Returns:
            Dict: Cleaned results
        """
        if "reviews" in results:
            for review in results["reviews"]:
                # 1) guarantee ≥1 label
                self._ensure_at_least_one_label(review)
    
                # 2) validate / fix every label
                review["labels"] = [
                    self.validation_service.validate_and_fix_label(lbl)
                    for lbl in review["labels"]
                ]
    
        return results