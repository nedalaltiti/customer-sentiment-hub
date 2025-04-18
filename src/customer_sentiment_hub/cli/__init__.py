"""
Command-line interface for Customer Sentiment Hub.

This package provides a CLI for interacting with the sentiment analysis
capabilities, allowing for review analysis, configuration management,
and starting the API server from the command line.
"""

from customer_sentiment_hub.cli.app import app, run_cli
from customer_sentiment_hub.cli.commands import analyze_command, version_command, server_command

__all__ = [
    "app",          
    "run_cli",     
    "analyze_command",  
    "version_command",  
    "server_command"   
]