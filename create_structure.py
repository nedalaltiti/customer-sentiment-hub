#!/usr/bin/env python3
"""
Advanced Project Structure Generator

A professional utility script that creates a pre-defined directory structure 
for a Python project with empty files, ensuring a consistent starting point
for project development.
"""

import argparse
import logging
import os
import pathlib
import sys
import time
from typing import Dict, Union, Any, Optional

# Try to import optional dependencies for enhanced experience
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class ProjectStructureGenerator:
    """
    Generates a predefined project directory structure with empty files.
    
    This class handles the creation of directories and files according to
    a provided structure definition, with logging, progress reporting, and
    error handling.
    """
    
    def __init__(
        self, 
        structure: Dict[str, Any], 
        base_dir: pathlib.Path,
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the project structure generator.
        
        Args:
            structure: Dictionary defining the project structure
            base_dir: Base directory where the structure will be created
            dry_run: If True, only show what would be done without making changes
            verbose: If True, show detailed logs
        """
        self.structure = structure
        self.base_dir = base_dir
        self.dry_run = dry_run
        self.verbose = verbose
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize rich console if available
        if RICH_AVAILABLE:
            self.console = Console()
            self.progress: Optional[Progress] = None
            self.main_task: Optional[TaskID] = None
        else:
            self.console = None
    
    def _setup_logging(self) -> None:
        """Configure logging based on verbosity level."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        
        if RICH_AVAILABLE:
            logging.basicConfig(
                level=log_level,
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(rich_tracebacks=True)]
            )
        else:
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        self.logger = logging.getLogger("project-generator")
    
    def _print_header(self) -> None:
        """Print a stylish header for the tool."""
        if RICH_AVAILABLE:
            header_text = "\n[bold cyan]Project Structure Generator[/bold cyan]\n"
            header_text += f"[green]Target directory:[/green] {self.base_dir}\n"
            header_text += f"[green]Mode:[/green] {'Dry run (no changes will be made)' if self.dry_run else 'Normal operation'}\n"
            
            self.console.print(Panel(header_text, expand=False))
        else:
            print("\n=== Project Structure Generator ===")
            print(f"Target directory: {self.base_dir}")
            print(f"Mode: {'Dry run (no changes will be made)' if self.dry_run else 'Normal operation'}")
            print("=====================================\n")
    
    def _start_progress(self) -> None:
        """Initialize the progress display if Rich is available."""
        if RICH_AVAILABLE:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}[/bold blue]"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console
            )
            self.progress.start()
            self.main_task = self.progress.add_task("[cyan]Creating project structure...", total=100)
    
    def _end_progress(self) -> None:
        """Finalize the progress display if Rich is available."""
        if RICH_AVAILABLE and self.progress:
            self.progress.update(self.main_task, completed=100)
            self.progress.stop()
    
    def _update_progress(self, advance: float) -> None:
        """Update the progress bar if Rich is available."""
        if RICH_AVAILABLE and self.progress and self.main_task is not None:
            self.progress.update(self.main_task, advance=advance)
    
    def _calculate_total_items(self, structure: Dict[str, Any]) -> int:
        """
        Calculate the total number of items to create.
        
        Args:
            structure: Dictionary defining the structure
            
        Returns:
            int: Total number of items (files and directories)
        """
        count = 0
        for name, content in structure.items():
            count += 1  # Count this item
            if isinstance(content, dict):
                # Recursively count items in subdirectories
                count += self._calculate_total_items(content)
        return count
    
    def create_structure(self) -> None:
        """Create the project structure according to the definition."""
        self._print_header()
        self._start_progress()
        
        # Calculate total for progress tracking
        total_items = self._calculate_total_items(self.structure)
        progress_increment = 100.0 / total_items if total_items > 0 else 100.0
        
        try:
            self._create_structure_recursive(self.base_dir, self.structure, progress_increment)
            
            if RICH_AVAILABLE:
                if self.dry_run:
                    self.console.print("\n[bold yellow]Dry run completed. No files were created.[/bold yellow]")
                else:
                    self.console.print("\n[bold green]Project structure created successfully![/bold green]")
            else:
                if self.dry_run:
                    print("\nDry run completed. No files were created.")
                else:
                    print("\nProject structure created successfully!")
                    
        except Exception as e:
            self.logger.error(f"Error creating project structure: {str(e)}", exc_info=self.verbose)
            if RICH_AVAILABLE:
                self.console.print(f"\n[bold red]Error creating project structure: {str(e)}[/bold red]")
            sys.exit(1)
        finally:
            self._end_progress()
    
    def _create_structure_recursive(
        self, 
        base_path: pathlib.Path, 
        structure: Dict[str, Any],
        progress_increment: float
    ) -> None:
        """
        Recursively create a directory structure with files.
        
        Args:
            base_path: The base path to create the structure under
            structure: Dictionary defining the structure
            progress_increment: Amount to advance the progress bar for each item
        """
        for name, content in structure.items():
            path = base_path / name
            
            if isinstance(content, dict):
                # This is a directory with content
                if not self.dry_run:
                    os.makedirs(path, exist_ok=True)
                
                # Log the directory creation
                if RICH_AVAILABLE:
                    self.logger.info(f"Created directory: [bold blue]{path}[/bold blue]")
                else:
                    self.logger.info(f"Created directory: {path}")
                
                # Update progress
                self._update_progress(progress_increment)
                
                # Small delay for visual effect in progress reporting
                time.sleep(0.01)
                
                # Recursively process subdirectories and files
                self._create_structure_recursive(path, content, progress_increment)
            else:
                # This is a file
                if not self.dry_run:
                    # Create parent directory if it doesn't exist
                    path.parent.mkdir(exist_ok=True, parents=True)
                    
                    # Create an empty file
                    with open(path, "w") as f:
                        pass
                
                # Log the file creation
                if RICH_AVAILABLE:
                    self.logger.info(f"Created file: [bold green]{path}[/bold green]")
                else:
                    self.logger.info(f"Created file: {path}")
                
                # Update progress
                self._update_progress(progress_increment)
                
                # Small delay for visual effect in progress reporting
                time.sleep(0.01)


def main() -> None:
    """
    Main function to handle command-line arguments and run the generator.
    """
    parser = argparse.ArgumentParser(
        description="Generate a predefined project directory structure with empty files."
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be done without making any changes"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--base-dir", "-d",
        type=str,
        default=".",
        help="Base directory where the structure will be created (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Define the project structure
    structure = {
        "pyproject.toml": None,
        "Makefile": None,
        ".env.example": None,
        ".pre-commit-config.yaml": None,
        "README.md": None,
        "src": {
            "customer_sentiment_hub": {
                "__init__.py": None,
                "__main__.py": None,
                "config": {
                    "__init__.py": None,
                    "settings.py": None,
                    "environment.py": None,
                },
                "domain": {
                    "__init__.py": None,
                    "taxonomy.py": None,
                    "schema.py": None,
                    "validation.py": None,
                },
                "prompts": {
                    "__init__.py": None,
                    "templates.py": None,
                    "formatters.py": None,
                },
                "services": {
                    "__init__.py": None,
                    "llm_service.py": None,
                    "gemini_service.py": None,
                    "processor.py": None,
                },
                "utils": {
                    "__init__.py": None,
                    "logging.py": None,
                    "result.py": None,
                    "helpers.py": None,
                },
                "cli": {
                    "__init__.py": None,
                    "commands.py": None,
                    "app.py": None,
                },
            }
        },
        "tests": {
            "__init__.py": None,
            "conftest.py": None,
            "unit": {
                "__init__.py": None,
                "test_taxonomy.py": None,
                "test_schema.py": None,
                "test_validation.py": None,
            },
            "integration": {
                "__init__.py": None,
                "test_analyzer.py": None,
            },
            "fixtures": {
                "__init__.py": None,
                "reviews.json": None,
                "responses.json": None,
            },
        },
        "docs": {
            "index.md": None,
            "user_guide.md": None,
            "api.md": None,
            "development.md": None,
        }
    }
    
    # Get the base directory
    base_dir = pathlib.Path(args.base_dir).resolve()
    
    # Run the generator
    generator = ProjectStructureGenerator(
        structure=structure,
        base_dir=base_dir,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    generator.create_structure()


if __name__ == "__main__":
    main()