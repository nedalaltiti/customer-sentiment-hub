"""
Main entry point for Customer Sentiment Hub.

This module serves as the primary entry point when the package is executed directly:
    python -m customer_sentiment_hub [command] [options]

It intelligently determines whether to start the API server or CLI based on arguments:
- With no arguments: Starts the API server with default settings
- With 'server' command: Starts the API server with custom options
- With other commands: Runs the CLI with the specified command

This dual-functionality approach enables flexibility in deployment while
maintaining consistency in configuration and behavior.
"""

import sys
import logging
from typing import List, Optional

from customer_sentiment_hub.utils.logging import configure_logging

def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point with intelligent API/CLI routing based on arguments.
    
    Args:
        args: Command line arguments (uses sys.argv if None)
        
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    # Parse arguments with default to empty list
    actual_args = args if args is not None else sys.argv[1:]
    
    # Configure logging
    configure_logging()
    logger = logging.getLogger("customer_sentiment_hub")
    
    try:
        # Determine whether to run API server or CLI
        if not actual_args or actual_args[0] == 'server':
            # Start API server
            logger.info("Starting API server mode")
            from customer_sentiment_hub.api.app import start as start_api
            
            # Extract server parameters if provided
            server_args = actual_args[1:] if actual_args and actual_args[0] == 'server' else []
            
            # Parse server args (simple implementation - can be enhanced)
            host = None
            port = None
            reload = False
            
            i = 0
            while i < len(server_args):
                if server_args[i] in ['--host'] and i + 1 < len(server_args):
                    host = server_args[i + 1]
                    i += 2
                elif server_args[i] in ['--port', '-p'] and i + 1 < len(server_args):
                    try:
                        port = int(server_args[i + 1])
                    except ValueError:
                        logger.error(f"Invalid port: {server_args[i + 1]}")
                        return 1
                    i += 2
                elif server_args[i] == '--reload':
                    reload = True
                    i += 1
                else:
                    i += 1
            
            # Start the API server
            start_api(host=host, port=port, reload=reload)
            return 0
        else:
            # Run CLI command
            logger.info(f"Starting CLI mode with command: {actual_args[0]}")
            from customer_sentiment_hub.cli.app import run_cli
            return run_cli(actual_args)
            
    except KeyboardInterrupt:
        # Handle graceful termination
        logger.info("Operation cancelled by user")
        print("\nOperation cancelled by user")
        return 130  # Standard exit code for SIGINT
        
    except Exception as e:
        # Handle unexpected errors
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())