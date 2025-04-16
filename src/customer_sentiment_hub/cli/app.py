"""CLI application for Customer Sentiment Hub."""

import typer

from customer_sentiment_hub.cli.commands import analyze_command, version_command

app = typer.Typer(
    name="sentiment-hub",
    help="Customer Sentiment Hub - A tool for analyzing customer sentiment in debt resolution reviews"
)

app.command(name="analyze")(analyze_command)
app.command(name="version")(version_command)

if __name__ == "__main__":
    app()