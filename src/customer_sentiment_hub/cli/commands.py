"""CLI commands for the Customer Sentiment Hub."""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.services.gemini_service import GeminiService
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.utils.helpers import extract_review_texts, load_json_file
from customer_sentiment_hub.utils.logging import configure_logging

console = Console()
logger = logging.getLogger(__name__)


def analyze_command(
    text: List[str] = typer.Option(None, "--text", "-t", help="Text to analyze"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to analyze"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
    batch_size: Optional[int] = typer.Option(
        None, "--batch-size", "-b", help="Batch size for processing"
    ),
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Confidence threshold"
    ),
):
    """Analyze customer reviews for sentiment and categorization."""
    configure_logging()
    
    # Initialize services
    validation_service = ValidationService()
    
    gemini_service = GeminiService(
        gemini_settings=settings.gemini,
        google_settings=settings.google_cloud,
        validation_service=validation_service,
    )
    
    processing_settings = settings.processing
    if batch_size is not None:
        processing_settings.batch_size = batch_size
    if threshold is not None:
        processing_settings.confidence_threshold = threshold
    
    processor = ReviewProcessor(
        llm_service=gemini_service,
        settings=processing_settings,
    )
    
    # Get review texts to analyze
    review_texts = []
    
    if text:
        review_texts = text
    elif file:
        try:
            if file.suffix.lower() == ".json":
                data = load_json_file(str(file))
                review_texts = extract_review_texts(data)
            else:
                with open(file, 'r', encoding='utf-8') as f:
                    review_texts = [line.strip() for line in f if line.strip()]
            
            if not review_texts:
                console.print(f"[bold red]Error:[/] No reviews found in {file}")
                return
            
            console.print(f"Loaded [bold]{len(review_texts)}[/] reviews from {file}")
        except Exception as e:
            console.print(f"[bold red]Error loading file:[/] {str(e)}")
            return
    else:
        console.print("[bold yellow]No input provided.[/] Please specify --text or --file")
        return
    
    # Process reviews
    with console.status(f"Analyzing {len(review_texts)} reviews..."):
        result = asyncio.run(processor.process_reviews(review_texts))
    
    # Display results
    if result.is_success():
        data = result.value
        num_reviews = len(data.get("reviews", []))
        console.print(f"[bold green]Successfully analyzed {num_reviews} reviews[/]")
        
        # Display sample results
        if num_reviews > 0:
            sample_size = min(num_reviews, 2)
            console.print("\n[bold]Sample Results:[/]")
            
            for i in range(sample_size):
                review = data["reviews"][i]
                console.print(f"\n[bold]Review {i+1}:[/] {review['text'][:100]}...")
                
                # Create a table for labels
                table = Table(show_header=True, header_style="bold")
                table.add_column("Category")
                table.add_column("Subcategory")
                table.add_column("Sentiment")
                
                for label in review["labels"]:
                    sentiment_color = {
                        "Positive": "green",
                        "Negative": "red",
                        "Neutral": "yellow"
                    }.get(label["sentiment"], "white")
                    
                    table.add_row(
                        label["category"],
                        label["subcategory"],
                        f"[{sentiment_color}]{label['sentiment']}[/]"
                    )
                
                console.print(table)
        
        # Save results if output path is provided
        if output:
            try:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                console.print(f"[bold green]Results saved to {output}[/]")
            except Exception as e:
                console.print(f"[bold red]Error saving results:[/] {str(e)}")
    else:
        console.print(f"[bold red]Error analyzing reviews:[/] {result.error}")


def version_command():
    """Display version information."""
    console.print("[bold]Customer Sentiment Hub[/] version 0.1.0")