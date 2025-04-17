"""
Main entry point for Customer Sentiment Hub.

Usage:
  # launch HTTP API:
  python -m customer_sentiment_hub server [--host HOST] [--port PORT] [--reload]

  # or run CLI:
  python -m customer_sentiment_hub <your‑cli‑command> [options]
"""

import sys
import logging
from typing import List, Optional

from customer_sentiment_hub.utils.logging import configure_logging

def main(args: Optional[List[str]] = None) -> int:
    actual_args = args if args is not None else sys.argv[1:]
    configure_logging()  # uses defaults from settings
    logger = logging.getLogger("customer_sentiment_hub")

    try:
        # No args or "server" → HTTP API mode
        if not actual_args or actual_args[0] == "server":
            logger.info("🌐 Starting HTTP API mode")
            from customer_sentiment_hub.api.app import start as start_server

            # parse optional flags: --host, --port, --reload
            host = None
            port = None
            reload = False
            i = 1 if actual_args and actual_args[0] == "server" else 0
            while i < len(actual_args):
                arg = actual_args[i]
                if arg == "--host" and i + 1 < len(actual_args):
                    host = actual_args[i + 1]; i += 2
                elif arg in ("--port", "-p") and i + 1 < len(actual_args):
                    try:
                        port = int(actual_args[i + 1])
                    except ValueError:
                        logger.error("Invalid port: %s", actual_args[i+1])
                        return 1
                    i += 2
                elif arg == "--reload":
                    reload = True; i += 1
                else:
                    i += 1

            start_server(host=host, port=port, reload=reload)
            return 0

        # otherwise → CLI mode
        else:
            cmd = actual_args[0]
            logger.info("Starting CLI mode with command: %s", cmd)
            from customer_sentiment_hub.cli.app import run_cli
            return run_cli(actual_args)

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("✋ Operation cancelled by user")
        return 130

    except Exception as e:
        logger.exception("Unhandled exception in main(): %s", e)
        print(f" Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
