"""Review processing service."""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Union

from customer_sentiment_hub.config.settings import ProcessingSettings
from customer_sentiment_hub.services.llm_service import LLMService
from customer_sentiment_hub.utils.result import Result, Success, Error

logger = logging.getLogger(__name__)


class ReviewProcessor:
    """Service for processing customer reviews."""
    
    def __init__(
        self,
        llm_service: LLMService,
        settings: ProcessingSettings,
    ):
        """
        Initialize the review processor.
        
        Args:
            llm_service: LLM service for analyzing reviews
            settings: Processing settings
        """
        self.llm_service = llm_service
        self.settings = settings
        
        logger.info(
            f"Initialized ReviewProcessor with batch size {settings.batch_size}"
        )
    
    async def process_single_review(self, review_text: str, review_id: Optional[str] = None) -> Result[Dict]:
        """
        Process a single review.
        
        Args:
            review_text: The review text to process
            review_id: Optional identifier for the review
            
        Returns:
            Result containing the processed review or error
        """
        review_ids = [review_id] if review_id is not None else None
        return await self.process_reviews([review_text], review_ids)
    
    async def process_reviews(self, review_texts: List[str], review_ids: Optional[List[str]] = None) -> Result[Dict]:
        """
        Process multiple reviews.
        
        Args:
            review_texts: List of review texts to process
            review_ids: Optional list of IDs for the reviews (must match length of review_texts)
            
        Returns:
            Result containing the processed reviews or error
        """
        # Validate inputs
        if not review_texts:
            return Error("No reviews provided for analysis")
        
        # Handle review IDs
        if review_ids is not None:
            if len(review_ids) != len(review_texts):
                return Error("Number of review IDs must match number of review texts")
        else:
            # Generate sequential IDs for backward compatibility
            review_ids = [f"{1000 + i}" for i in range(len(review_texts))]
        
        if len(review_texts) <= self.settings.batch_size:
            # Process directly if the batch is small enough
            result = await self.llm_service.analyze_reviews(review_texts)
            
            # Update review IDs if successful
            if result.is_success() and "reviews" in result.value:
                for i, review in enumerate(result.value["reviews"]):
                    if i < len(review_ids):
                        review["review_id"] = review_ids[i]
                        
            return result
        else:
            # Process in batches for larger sets
            return await self._process_in_batches(review_texts, review_ids)
    
    async def _process_in_batches(self, review_texts: List[str], review_ids: List[str]) -> Result[Dict]:
        """
        Process reviews in batches.
        
        Args:
            review_texts: List of review texts to process
            review_ids: List of IDs for the reviews
            
        Returns:
            Result containing all processed reviews or error
        """
        # Initialize result with empty reviews list
        final_result = {"reviews": []}
        
        # Process in batches
        num_batches = (len(review_texts) + self.settings.batch_size - 1) // self.settings.batch_size
        
        logger.info(f"Processing {len(review_texts)} reviews in {num_batches} batches")
        
        for i in range(0, len(review_texts), self.settings.batch_size):
            batch_number = i // self.settings.batch_size + 1
            logger.info(f"Processing batch {batch_number}/{num_batches}")
            
            # Get current batch of texts and IDs
            batch_texts = review_texts[i:i + self.settings.batch_size]
            batch_ids = review_ids[i:i + self.settings.batch_size]
            
            # Process batch
            batch_result = await self.llm_service.analyze_reviews(batch_texts)
            
            if batch_result.is_success():
                # Update review IDs to preserve user-provided IDs
                batch_data = batch_result.value
                if "reviews" in batch_data:
                    for j, review in enumerate(batch_data["reviews"]):
                        if j < len(batch_ids):
                            review["review_id"] = batch_ids[j]
                    
                    # Add to final result
                    final_result["reviews"].extend(batch_data["reviews"])
            else:
                # Handle error case
                error_msg = f"Error processing batch {batch_number}: {batch_result.error}"
                logger.error(error_msg)
                
                # Add placeholder entries for failed batch
                for j, (text, review_id) in enumerate(zip(batch_texts, batch_ids)):
                    final_result["reviews"].append({
                        "review_id": review_id,  # Use the provided ID
                        "text": text,
                        "labels": [{
                            "category": "Miscellaneous",
                            "subcategory": "Other",
                            "sentiment": "Neutral",
                            "error": "Processing failed"
                        }],
                        "processing_error": error_msg
                    })
        
        logger.info(f"Completed processing {len(review_texts)} reviews")
        return Success(final_result)
    
    async def process_from_file(
        self, file_path: str, output_path: Optional[str] = None
    ) -> Result[Dict]:
        """
        Process reviews from a file and save results.
        
        Args:
            file_path: Path to the input file (JSON or TXT)
            output_path: Path to save the results (default: input_file_results.json)
            
        Returns:
            Result containing processed reviews or error
        """
        try:
            # Determine file type and load reviews
            review_texts = []
            review_ids = []
            
            if file_path.endswith('.json'):
                # Load reviews from JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract review texts and IDs
                if isinstance(data, list):
                    # Check if list contains objects with review_id and review_text
                    if data and isinstance(data[0], dict) and 'review_id' in data[0] and 'review_text' in data[0]:
                        review_ids = [item['review_id'] for item in data]
                        review_texts = [item['review_text'] for item in data]
                    else:
                        # Treat list items as review texts
                        review_texts = data
                elif isinstance(data, dict):
                    if 'reviews' in data:
                        # New format with reviews array
                        if data['reviews'] and isinstance(data['reviews'][0], dict):
                            if 'review_id' in data['reviews'][0] and 'review_text' in data['reviews'][0]:
                                # New format with review_id and review_text
                                review_ids = [item['review_id'] for item in data['reviews']]
                                review_texts = [item['review_text'] for item in data['reviews']]
                            elif 'text' in data['reviews'][0]:
                                # Old format with text field
                                review_texts = [r.get('text', '') for r in data['reviews'] if 'text' in r]
                    else:
                        # Handle key-value pairs as reviews
                        review_texts = []
                        for key, value in data.items():
                            if isinstance(value, str):
                                review_ids.append(key)
                                review_texts.append(value)
            else:
                # Load reviews from text file (one per line)
                with open(file_path, 'r', encoding='utf-8') as f:
                    review_texts = [line.strip() for line in f if line.strip()]
            
            if not review_texts:
                return Error(f"No reviews found in {file_path}")
            
            logger.info(f"Loaded {len(review_texts)} reviews from {file_path}")
            
            # Process reviews
            result = await self.process_reviews(review_texts, review_ids if review_ids else None)
            
            if result.is_success():
                # Save results if output path is provided
                if output_path is None:
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_path = f"{base_name}_results.json"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result.value, f, indent=2)
                
                logger.info(f"Results saved to {output_path}")
            
            return result
        
        except Exception as e:
            error_msg = f"Error processing file {file_path}: {str(e)}"
            logger.error(error_msg)
            return Error(error_msg)