"""
CLI application for Customer Sentiment Hub.

This module defines the main Typer application and its command structure,
providing a user-friendly command-line interface for the sentiment analysis tools.
"""

import sys
import logging
from typing import List, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from customer_sentiment_hub.cli.commands import analyze_command, version_command, server_command
from customer_sentiment_hub.utils.logging import configure_logging
from customer_sentiment_hub import __version__

# Create console for rich output
console = Console()

# Create the Typer application with rich help formatting
app = typer.Typer(
    name="sentiment-hub",
    help="Customer Sentiment Hub - AI-powered analysis of customer sentiment in reviews",
    add_completion=True,
    rich_markup_mode="rich",
)

# Register commands
app.command(name="analyze", help="Analyze customer reviews for sentiment and categories")(analyze_command)
app.command(name="version", help="Show version information")(version_command)
app.command(name="server", help="Start the API server")(server_command)

# Configure logging
logger = logging.getLogger("customer_sentiment_hub.cli")

def run_cli(args: Optional[List[str]] = None) -> int:
    """
    Run the CLI application with proper error handling and logging.
    
    Args:
        args: Command line arguments (uses sys.argv if None)
        
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Configure logging with rich output
    configure_logging(
        log_level="INFO",
        console_output=True,
        file_output=True
    )
    
    # Set up rich handler for terminal output
    rich_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        show_time=False
    )
    
    # Add rich handler to root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            root_logger.removeHandler(handler)
    root_logger.addHandler(rich_handler)
    
    try:
        # Run the Typer app
        app(args)
        return 0
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logger.exception(f"Error running CLI: {str(e)}")
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(run_cli())