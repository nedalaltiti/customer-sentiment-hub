# src/customer_sentiment_hub/services/freshdesk_service.py

"""Service for integrating with Freshdesk."""

import logging
import json
import os
from typing import Dict, List, Any, Optional
import aiohttp
from pydantic import BaseModel
from pathlib import Path

# Imports for HTML parsing and templating
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

from customer_sentiment_hub.utils.result import Result, Success, Error
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.api.models import FreshdeskWebhookPayload 
from customer_sentiment_hub.config.settings import (settings, FreshdeskSettings)

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
try:
    jinja_env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"])
    )
    # Load the template with inline styles
    freshdesk_note_template = jinja_env.get_template("freshdesk_note_template_inline_styles.html")
    logger.info(f"Successfully loaded Freshdesk note template from {TEMPLATE_DIR}")
except TemplateNotFound:
    freshdesk_note_template = None
    logger.warning(f"Freshdesk note template not found in {TEMPLATE_DIR}. Notes will use basic formatting.")
except Exception as e:
    freshdesk_note_template = None
    logger.error(f"Error initializing Jinja2 environment: {e}", exc_info=True)
    logger.warning("Notes will use basic formatting due to Jinja2 error.")

class FreshdeskService:
    """Service for interacting with the Freshdesk REST API."""

    def __init__(self, cfg: Optional[FreshdeskSettings] = None) -> None:
        """
        Parameters
        ----------
        cfg : FreshdeskSettings | None
            Injected config (useful for tests). Defaults to global `settings.freshdesk`.
        """
        self.cfg: FreshdeskSettings = cfg or settings.freshdesk

        if not self.cfg.is_configured:
            self._active = False
            logger.warning(
                "FreshdeskService inactive – missing API key or domain "
                "(api_key=%s, domain=%s)",
                bool(self.cfg.api_key), bool(self.cfg.domain)
            )
            return

        # Build base URL
        self.base_url: str = (
            f"https://{self.cfg.sanitised_domain}.freshdesk.com/api/v2"
        )
        self.auth = aiohttp.BasicAuth(self.cfg.api_key, password="X")
        self.max_tag_len: int = self.cfg.max_tag_len   # expose for _clean_tag
        self._active = True

        logger.info(
            "FreshdeskService ready (domain=%s, max_tag_len=%s)",
            self.cfg.sanitised_domain, self.max_tag_len
        )


    def _check_active(self) -> Result[None]:
        """Return Success / Error if service is (not) configured."""
        if not self._active:
            return Error("Freshdesk service is not active - missing configuration")
        return Success(None)
    
    async def get_ticket(self, ticket_id: int) -> Result[Dict]:
        active_check = self._check_active()
        if not active_check.is_success():
            return active_check

        url = f"{self.base_url}/tickets/{ticket_id}"
        params = None
        headers = {"Content-Type": "application/json"}

        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        ticket = await response.json()
                        return Success(ticket)
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to get ticket {ticket_id}: {response.status} - {error_text}")
                        return Error(f"Failed to get ticket: {response.status} - {error_text}")
        except Exception as e:
            logger.exception(f"Exception occurred while getting ticket {ticket_id}")
            return Error(f"Error getting ticket {ticket_id}: {str(e)}")

    def _extract_clean_review_text(self, html_content: str) -> str:
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "lxml")
            original_request_div = soup.find("div", id="ticket_original_request")
            if original_request_div:
                quoted_text_span = original_request_div.find("span", class_="quoted-text")
                if quoted_text_span:
                    clean_text = quoted_text_span.get_text(separator=" ", strip=True)
                    if clean_text:
                        logger.info("Extracted review text from span.quoted-text")
                        return clean_text
            if original_request_div:
                clean_text = original_request_div.get_text(separator=" ", strip=True)
                if clean_text and len(clean_text) < 10000:
                    logger.info("Extracted review text from div#ticket_original_request (fallback 1)")
                    return clean_text
            soup_raw = BeautifulSoup(html_content, "lxml")
            for tag in soup_raw(["script", "style"]):
                tag.decompose()
            clean_text = soup_raw.get_text(separator=" ", strip=True)
            logger.info("Extracted review text from raw HTML (fallback 2)")
            return clean_text
        except Exception as e:
            logger.error(f"Error parsing HTML to extract review text: {e}", exc_info=True)
            return html_content 

    def _format_note_body(self, clean_review_text: str, analysis: Dict) -> str:
        context = {
            "original_text": clean_review_text,
            "analysis": analysis
        }
        
        if freshdesk_note_template:
            try:
                # Use the template with inline styles
                return freshdesk_note_template.render(context)
            except Exception as e:
                logger.error(f"Error rendering Jinja2 template: {e}", exc_info=True)
        
        logger.warning("Using fallback basic HTML formatting for Freshdesk note.")
        html_parts = [
            "<div>",
            "<h4>Sentiment Analysis Results</h4>"
        ]
        if clean_review_text:
            html_parts.append(f"<p><strong>Original Text:</strong><br>{clean_review_text}</p>")
        if analysis and analysis.get("language"):
            lang = analysis["language"].upper()
            html_parts.append(
                f'<p><strong>Language:</strong> '
                f'<span style="display:inline-block; padding:2px 6px; '
                f'background:#f0f0f0; border-radius:3px; '
                f'font-weight:bold;">{lang}</span></p>'
            )
        labels = analysis.get("labels", [])
        if labels:
            html_parts.append("<table border=\"1\" style=\"border-collapse: collapse; width: 100%; margin-top: 10px;\">")
            html_parts.append("<tr><th>Category</th><th>Subcategory</th><th>Sentiment</th></tr>")
            for label in labels:
                category = label.get("category", "")
                subcategory = label.get("subcategory", "")
                sentiment = label.get("sentiment", "")
                # Inline styles for fallback
                style = "color: #546E7A; font-weight: bold;"
                if sentiment.lower() == "positive": style = "color: #2E7D32; font-weight: bold;"
                elif sentiment.lower() == "negative": style = "color: #C62828; font-weight: bold;"
                html_parts.append(f"<tr><td>{category}</td><td>{subcategory}</td><td style=\"{style}\">{sentiment}</td></tr>")
            html_parts.append("</table>")
        else:
             html_parts.append("<p>No specific labels identified.</p>")
        html_parts.append("<details style=\"margin-top: 15px;\"><summary>View raw analysis data</summary>")
        html_parts.append(f"<pre>{json.dumps(analysis, indent=2)}</pre></details>")
        html_parts.append("</div>")
        return "".join(html_parts)

    async def update_ticket_with_analysis(self, ticket_id: int, clean_review_text: str, analysis: Dict) -> Result[Dict]:
        active_check = self._check_active()
        if not active_check.is_success():
            return active_check
            
        url = f"{self.base_url}/tickets/{ticket_id}"
        headers = {"Content-Type": "application/json"}

        labels = analysis.get("labels", [])
        # tags = set()
        def _clean_tag(raw: str) -> str:
            cleaned = raw.replace(" ", "_").replace("&", "and").lower()
            if len(cleaned) > self.cfg.max_tag_len:
                logger.debug("Trimming tag '%s' → '%s'", cleaned, cleaned[: self.cfg.max_tag_len])
            return cleaned[: self.cfg.max_tag_len]


        tags: set[str] = set()
        for label in labels:
            category = label.get("category", "")
            subcategory = label.get("subcategory", "")
            sentiment = label.get("sentiment", "")
            if category:
                tags.add(_clean_tag(f"cat_{category}"))
            if subcategory:
                tags.add(_clean_tag(f"sub_{subcategory}"))
            if sentiment:
                tags.add(_clean_tag(f"sent_{sentiment}"))

        update_payload = {"tags": list(tags)}

        note_html_body = self._format_note_body(clean_review_text, analysis)
        note_payload = {"body": note_html_body, "private": True}

        try:
            async with aiohttp.ClientSession(auth=self.auth) as session:
                if update_payload.get("tags"):
                    # Corrected f-string syntax using single quotes for dictionary key
                    logger.info(f"Attempting to update ticket {ticket_id} tags: {update_payload['tags']}") 
                    async with session.put(url, json=update_payload, headers=headers) as response:
                        if response.status == 200:
                            logger.info(f"Successfully updated tags for ticket {ticket_id}")
                        else:
                            error_text = await response.text()
                            logger.warning(f"Failed to update tags for ticket {ticket_id}: {response.status} - {error_text}")
                else:
                    logger.info(f"No tags generated to update for ticket {ticket_id}.")
                        
                note_url = f"{self.base_url}/tickets/{ticket_id}/notes"
                logger.info(f"Attempting to add analysis note to ticket {ticket_id}")
                async with session.post(note_url, json=note_payload, headers=headers) as note_response:
                    if note_response.status == 201:
                        logger.info(f"Successfully added analysis note to ticket {ticket_id}")
                    else:
                        note_error_text = await note_response.text()
                        logger.warning(f"Failed to add note to ticket {ticket_id}: {note_response.status} - {note_error_text}")
                
                return Success({"message": f"Processed ticket {ticket_id}. Check ticket for updates and notes."}) 

        except Exception as e:
            logger.exception(f"Exception occurred while updating ticket {ticket_id}")
            return Error(f"Error updating ticket {ticket_id}: {str(e)}")

    async def process_ticket_reviews(self, processor: ReviewProcessor, ticket_id: int, raw_html_description: Optional[str] = None) -> Result[Dict]:
        active_check = self._check_active()
        if not active_check.is_success():
            return active_check
            
        logger.info(f"Starting processing for ticket ID: {ticket_id}")
        
        if not raw_html_description:
            logger.info(f"No HTML description provided directly. Fetching ticket {ticket_id} from Freshdesk API.")
            ticket_result = await self.get_ticket(ticket_id)
            if not ticket_result.is_success():
                return ticket_result
            ticket = ticket_result.value
            raw_html_description = ticket.get("description", "") 
        
        if not raw_html_description:
            logger.warning(f"Ticket {ticket_id} has no HTML description. Skipping analysis.")
            return Error("Ticket has no HTML description")
        
        clean_review_text = self._extract_clean_review_text(raw_html_description)
        if not clean_review_text:
             logger.warning(f"Could not extract clean review text from HTML for ticket {ticket_id}. Skipping analysis.")
             return Error("Could not extract clean review text from HTML")

        review_id = f"fd_{ticket_id}"
        logger.info(f"Sending cleaned ticket {ticket_id} description (length: {len(clean_review_text)}) for analysis.")
        analysis_result = await processor.process_reviews([clean_review_text], [review_id])
        
        if not analysis_result.is_success():
            logger.error(f"Analysis failed for ticket {ticket_id}: {analysis_result.error}")
            return analysis_result
        
        processed_reviews = analysis_result.value.get("reviews", [])
        if not processed_reviews:
             logger.warning(f"Analysis returned no processed reviews for ticket {ticket_id}.")
             analysis_data = {"review_id": review_id, "review_text": clean_review_text, "labels": [], "language": "unknown" }
        else:
            analysis_data = processed_reviews[0]

        update_result = await self.update_ticket_with_analysis(ticket_id, clean_review_text, analysis_data)
        return update_result

    async def handle_webhook_event(self, processor: ReviewProcessor, payload: FreshdeskWebhookPayload):
        """
        Handles the incoming webhook event from Freshdesk.
        This is triggered automatically when a new ticket is created.
        
        Args:
            processor: ReviewProcessor instance for sentiment analysis
            payload: Validated webhook payload containing ticket info
        """
        if not payload.reviews:
            logger.error("[Webhook Handler] Received empty reviews list in payload.")
            return
            
        review_item = payload.reviews[0]
        ticket_id = review_item.review_id
        raw_html_description = review_item.review_text
        
        logger.info(f"[Webhook Handler] Processing ticket ID: {ticket_id} automatically")
        
        if raw_html_description:
            logger.info(f"[Webhook Handler] Processing ticket description (length: {len(raw_html_description)})")
        else:
            logger.info(f"[Webhook Handler] No description in payload, fetching from API")
            ticket_result = await self.get_ticket(ticket_id)
            if ticket_result.is_success():
                ticket_data = ticket_result.value
                raw_html_description = ticket_data.get("description", "")
                if not raw_html_description:
                    logger.warning(f"[Webhook Handler] Ticket {ticket_id} has no description to analyze")
                    return
            else:
                logger.error(f"[Webhook Handler] Failed to fetch ticket {ticket_id}: {ticket_result.error}")
                return
    
        # Process the ticket and add analysis results
        result = await self.process_ticket_reviews(processor, ticket_id, raw_html_description)
        
        if result.is_success():
            logger.info(f"[Webhook Handler] Successfully analyzed ticket {ticket_id} - Gemini results added as note")
        else:
            logger.error(f"[Webhook Handler] Failed to analyze ticket {ticket_id}: {result.error}")

    def validate_webhook_signature(self, headers: Dict[str, str], body: bytes) -> bool:
        """
        Validates a Freshdesk webhook signature.

        Args:
            headers: Request headers containing the signature
            body: Raw request body bytes

        Returns:
            bool: True if signature is valid or if no webhook_secret is configured
        """
        if not self.settings or not self.settings.webhook_secret:
            # If no secret configured, skip validation (development mode)
            return True

        try:
            received_signature = headers.get("X-Freshdesk-Signature")
            if not received_signature:
                logger.warning("No X-Freshdesk-Signature header in request")
                return False

            import hmac
            import hashlib
            calculated_signature = hmac.new(
                self.settings.webhook_secret.encode("utf-8"),
                body,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(calculated_signature, received_signature)

        except Exception as e:
            logger.exception(f"Error validating webhook signature: {str(e)}")
            return False