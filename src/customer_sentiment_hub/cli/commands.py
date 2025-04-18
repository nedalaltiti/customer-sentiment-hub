"""
Command implementations for the Customer Sentiment Hub CLI.

This module contains the actual implementations of the CLI commands,
separated from the application definition for better organization.
"""

from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from customer_sentiment_hub import __version__, ReviewProcessor, GeminiService, ValidationService
from customer_sentiment_hub.config.settings import settings
from customer_sentiment_hub.utils.helpers import load_json_file, save_json_file, extract_review_texts
from customer_sentiment_hub.api.app import start as start_api_server
from customer_sentiment_hub.utils.logging import configure_logging

# Create console for rich output
console = Console()

def analyze_command(
    input_file: Path = typer.Option(
        None, "--input", "-i", help="Input file containing reviews (JSON or TXT)"
    ),
    output_file: Path = typer.Option(
        None, "--output", "-o", help="Output file for analysis results (JSON)"
    ),
    text: List[str] = typer.Option(
        None, "--text", "-t", help="Review text to analyze (can be specified multiple times)"
    ),
    batch_size: int = typer.Option(
        5, "--batch-size", "-b", help="Batch size for processing reviews"
    ),
    model: str = typer.Option(
        settings.gemini.model_name, "--model", "-m", help="Model to use for analysis"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Analyze customer reviews for sentiment and categorization.
    
    This command processes reviews from a file or directly provided text,
    analyzing them for sentiment and categorizing them according to the
    customer sentiment taxonomy.
    """
    # Validate input sources
    if not input_file and not text:
        console.print("[bold red]Error:[/bold red] No input provided. Use --input or --text")
        raise typer.Exit(code=1)
    
    # Load reviews from input file if provided
    reviews: List[str] = []
    if input_file:
        if not input_file.exists():
            console.print(f"[bold red]Error:[/bold red] Input file not found: {input_file}")
            raise typer.Exit(code=1)
        
        try:
            # Determine file type and load accordingly
            if input_file.suffix.lower() in ('.json', '.jsonl'):
                data = load_json_file(input_file)
                reviews.extend(extract_review_texts(data))
            else:
                # Assume text file with one review per line
                with open(input_file, 'r', encoding='utf-8') as f:
                    reviews.extend([line.strip() for line in f if line.strip()])
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Failed to load input file: {str(e)}")
            raise typer.Exit(code=1)
    
    # Add reviews from command line arguments
    if text:
        reviews.extend(text)
    
    # Show summary of processing task
    console.print(Panel(
        f"[bold]Analyzing {len(reviews)} reviews[/bold]\n"
        f"Model: [cyan]{model}[/cyan]\n"
        f"Batch size: [cyan]{batch_size}[/cyan]",
        title="Customer Sentiment Analysis",
        border_style="blue"
    ))
    
    # Initialize services
    validation_service = ValidationService()
    gemini_service = GeminiService(
        gemini_settings=settings.gemini,
        google_settings=settings.google_cloud,
        validation_service=validation_service,
    )
    processor = ReviewProcessor(
        llm_service=gemini_service,
        settings=settings.processing,
    )
    
    # Process the reviews with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing reviews...", total=len(reviews))
        
        # The actual processing happens here
        result = processor.process_reviews(reviews)
        progress.update(task, completed=len(reviews))
    
    # Check result and display
    if not result.is_success():
        console.print(f"[bold red]Error:[/bold red] {result.error}")
        raise typer.Exit(code=1)
    
    # Display results summary
    display_analysis_results(result.value["reviews"], verbose)
    
    # Save results if output file specified
    if output_file:
        try:
            save_json_file(result.value, output_file)
            console.print(f"Results saved to [green]{output_file}[/green]")
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Failed to save output file: {str(e)}")
            raise typer.Exit(code=1)


def version_command(
    check_update: bool = typer.Option(
        False, "--check-update", help="Check for updates online"
    )
) -> None:
    """
    Display version information for Customer Sentiment Hub.
    
    Shows the current version and optionally checks for updates.
    """
    from customer_sentiment_hub import __version__
    
    # Create a table for version information
    table = Table(title="Customer Sentiment Hub", show_header=False, border_style="blue")
    table.add_column("Property", style="cyan")
    table.add_column("Value")
    
    # Add version information
    table.add_row("Version", __version__)
    table.add_row("Model", settings.gemini.model_name)
    table.add_row("Environment", settings.environment)
    
    # Display the table
    console.print(table)
    
    # Check for updates if requested
    if check_update:
        console.print("[yellow]Update checking not implemented yet[/yellow]")


def server_command(
    host: str = typer.Option(
        settings.host, "--host", help="Host address to bind server to"
    ),
    port: int = typer.Option(
        settings.port, "--port", "-p", help="Port number to listen on"
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development"
    ),
    workers: int = typer.Option(
        1, "--workers", "-w", help="Number of worker processes (for production)"
    ),
    log_level: str = typer.Option(
        settings.log_level, "--log-level", "-l", 
        help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
) -> None:
    """
    Start the Customer Sentiment Hub API server.
    
    This command launches the FastAPI application with the specified configuration.
    The server provides HTTP endpoints for sentiment analysis and review processing.
    
    For production deployment, consider:
    - Using multiple workers
    - Setting appropriate host/port
    - Configuring logging
    - Disabling reload
    
    For development:
    - Enable reload with --reload
    - Use DEBUG log level for detailed output
    - Use default host/port
    
    Examples:
        sentiment-hub server --reload
        sentiment-hub server --host 0.0.0.0 --port 8080 --workers 4
    """
    # Configure logging for the server
    configure_logging(log_level=log_level, console_output=True, file_output=True)
    
    # Create a rich console for nice output
    console = Console()
    
    # Display server configuration
    server_info = [
        f"[bold]API Server Configuration[/bold]",
        f"Host: [cyan]{host}[/cyan]",
        f"Port: [cyan]{port}[/cyan]",
        f"Workers: [cyan]{workers}[/cyan]",
        f"Auto-reload: [cyan]{'Enabled' if reload else 'Disabled'}[/cyan]",
        f"Log level: [cyan]{log_level}[/cyan]",
        f"Environment: [cyan]{settings.environment}[/cyan]",
    ]
    
    console.print(Panel(
        "\n".join(server_info),
        title="Customer Sentiment Hub API",
        border_style="green",
        expand=False
    ))
    
    # Set temporary process title
    try:
        import setproctitle
        setproctitle.setproctitle(f"sentiment-hub-server-{port}")
    except ImportError:
        pass
    
    # Start the server with configuration
    try:
        # Import here to avoid circular imports
        from customer_sentiment_hub.api.app import start as start_api
        
        # Start the API server
        start_api(
            host=host,
            port=port, 
            reload=reload,
            workers=workers,
            log_level=log_level
        )
    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] Missing dependencies: {str(e)}")
        console.print("Try installing with: [bold]pip install 'customer-sentiment-hub[api]'[/bold]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to start server: {str(e)}")
        raise typer.Exit(code=1)


def display_analysis_results(reviews: List[dict], verbose: bool = False) -> None:
    """
    Display analysis results in a readable format.
    
    Args:
        reviews: List of processed reviews
        verbose: Whether to show detailed output
    """
    # Summary table
    summary_table = Table(title="Analysis Summary", border_style="blue")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value")
    
    # Calculate summary statistics
    total_reviews = len(reviews)
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    category_counts = {}
    
    for review in reviews:
        # Extract dominant sentiment
        sentiments = [label["sentiment"].lower() for label in review.get("labels", [])]
        if sentiments:
            # Count the most common sentiment
            sentiment = max(set(sentiments), key=sentiments.count)
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        # Count categories
        for label in review.get("labels", []):
            category = label.get("category", "Unknown")
            category_counts[category] = category_counts.get(category, 0) + 1
    
    # Add summary statistics to table
    summary_table.add_row("Total Reviews", str(total_reviews))
    summary_table.add_row("Positive Sentiment", f"{sentiment_counts.get('positive', 0)} ({sentiment_counts.get('positive', 0)/total_reviews*100:.1f}%)")
    summary_table.add_row("Negative Sentiment", f"{sentiment_counts.get('negative', 0)} ({sentiment_counts.get('negative', 0)/total_reviews*100:.1f}%)")
    summary_table.add_row("Neutral Sentiment", f"{sentiment_counts.get('neutral', 0)} ({sentiment_counts.get('neutral', 0)/total_reviews*100:.1f}%)")
    
    # Display summary table
    console.print(summary_table)
    
    # If verbose, show detailed information for each review
    if verbose:
        console.print("\n[bold]Detailed Analysis[/bold]")
        for i, review in enumerate(reviews):
            console.print(f"\n[bold cyan]Review {i+1}:[/bold cyan]")
            console.print(f"ID: {review.get('review_id', 'N/A')}")
            console.print(f"Text: {review.get('text', '')[:100]}...")
            
            if "labels" in review and review["labels"]:
                label_table = Table(show_header=True, box=None)
                label_table.add_column("Category", style="green")
                label_table.add_column("Subcategory", style="yellow")
                label_table.add_column("Sentiment", style="cyan")
                
                for label in review["labels"]:
                    label_table.add_row(
                        label.get("category", "Unknown"),
                        label.get("subcategory", "Unknown"),
                        label.get("sentiment", "Unknown")
                    )
                
                console.print(label_table)
            else:
                console.print("[italic]No labels found[/italic]")