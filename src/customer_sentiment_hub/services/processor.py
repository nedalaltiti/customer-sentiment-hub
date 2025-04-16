"""Review processing service."""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

from customer_sentiment_hub.config.settings import ProcessingSettings
from customer_sentiment_hub.domain.schema import ReviewOutput
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
    
    async def process_single_review(self, review_text: str) -> Result[Dict]:
        """
        Process a single review.
        
        Args:
            review_text: The review text to process
            
        Returns:
            Result containing the processed review or error
        """
        return await self.process_reviews([review_text])
    
    async def process_reviews(self, review_texts: List[str]) -> Result[Dict]:
        """
        Process multiple reviews.
        
        Args:
            review_texts: List of review texts to process
            
        Returns:
            Result containing the processed reviews or error
        """
        if len(review_texts) <= self.settings.batch_size:
            # Process directly if the batch is small enough
            return await self.llm_service.analyze_reviews(review_texts)
        else:
            # Process in batches for larger sets
            return await self._process_in_batches(review_texts)
    
    async def _process_in_batches(self, review_texts: List[str]) -> Result[Dict]:
        """
        Process reviews in batches.
        
        Args:
            review_texts: List of review texts to process
            
        Returns:
            Result containing all processed reviews or error
        """
        # Initialize result with empty reviews list
        final_result = {"reviews": []}
        
        # Process in batches
        batches = [
            review_texts[i:i + self.settings.batch_size]
            for i in range(0, len(review_texts), self.settings.batch_size)
        ]
        
        logger.info(f"Processing {len(review_texts)} reviews in {len(batches)} batches")
        
        for i, batch in enumerate(batches):
            logger.info(f"Processing batch {i+1}/{len(batches)}")
            
            # Process batch
            batch_result = await self.llm_service.analyze_reviews(batch)
            
            if batch_result.is_success():
                # Update review IDs to maintain sequence
                batch_data = batch_result.value
                if "reviews" in batch_data:
                    start_idx = i * self.settings.batch_size
                    
                    for j, review in enumerate(batch_data["reviews"]):
                        review["review_id"] = str(1000 + start_idx + j)
                    
                    # Add to final result
                    final_result["reviews"].extend(batch_data["reviews"])
            else:
                # Handle error case
                error_msg = f"Error processing batch {i+1}: {batch_result.error}"
                logger.error(error_msg)
                
                # Add placeholder entries for failed batch
                start_idx = i * self.settings.batch_size
                
                for j, text in enumerate(batch):
                    final_result["reviews"].append({
                        "review_id": str(1000 + start_idx + j),
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
            
            if file_path.endswith('.json'):
                # Load reviews from JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract review texts
                if isinstance(data, list):
                    review_texts = data
                elif isinstance(data, dict) and 'reviews' in data:
                    review_texts = [r.get('text', '') for r in data['reviews'] if 'text' in r]
                else:
                    review_texts = []
                    for key, value in data.items():
                        if isinstance(value, str):
                            review_texts.append(value)
            else:
                # Load reviews from text file (one per line)
                with open(file_path, 'r', encoding='utf-8') as f:
                    review_texts = [line.strip() for line in f if line.strip()]
            
            if not review_texts:
                return Error(f"No reviews found in {file_path}")
            
            logger.info(f"Loaded {len(review_texts)} reviews from {file_path}")
            
            # Process reviews
            result = await self.process_reviews(review_texts)
            
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