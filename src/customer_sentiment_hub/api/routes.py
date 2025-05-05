# src/customer_sentiment_hub/api/routes.py

from fastapi import (
    APIRouter, Depends, FastAPI, HTTPException, Request, BackgroundTasks, status, Response
)
import json
import logging
import time
from datetime import datetime
from typing import Any, List, Optional, Union, Dict

from customer_sentiment_hub.api.models import (
    ReviewRequest, ReviewResponse, HealthCheckResponse, ErrorResponse, FreshdeskWebhookPayload
)
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.services.gemini_service import GeminiService
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.services.freshdesk_service import FreshdeskService

from customer_sentiment_hub.config.settings import settings


logger = logging.getLogger("customer_sentiment_hub")

api_prefix = settings.api_version
main_router = APIRouter(prefix=f"/{api_prefix}")


def get_processor(request: Request) -> ReviewProcessor:
    """Injects the ReviewProcessor from application state."""
    processor = getattr(request.app.state, "processor", None)
    if processor is None:
        logger.error("ReviewProcessor not found in application state.")
        raise HTTPException(status_code=500, detail="Internal server error: Processor not initialized")
    return processor

def get_gemini_service(request: Request) -> GeminiService:
    """Injects the GeminiService from application state."""
    gemini_service = getattr(request.app.state, "gemini_service", None)
    if gemini_service is None:
        logger.error("GeminiService not found in application state.")
        raise HTTPException(status_code=500, detail="Internal server error: Gemini service not initialized")
    return gemini_service

def get_validation_service(request: Request) -> ValidationService:
    """Injects the ValidationService from application state."""
    validation_service = getattr(request.app.state, "validation_service", None)
    if validation_service is None:
        logger.error("ValidationService not found in application state.")
        raise HTTPException(status_code=500, detail="Internal server error: Validation service not initialized")
    return validation_service

def get_freshdesk_service(request: Request) -> FreshdeskService:
    """Injects the FreshdeskService from application state."""
    freshdesk_service = getattr(request.app.state, "freshdesk_service", None)
    if freshdesk_service is None:
        # Log warning but don't raise 500 immediately, endpoint might not need it
        # Or, if Freshdesk integration is critical, raise HTTPException here.
        logger.warning("FreshdeskService not found in application state. Endpoints requiring it may fail.")
        # Depending on requirements, you might raise: 
        # raise HTTPException(status_code=500, detail="Internal server error: Freshdesk service not initialized")
    return freshdesk_service

# --- API Endpoints --- 

@main_router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="Check Service Health",
    responses={
        200: {"description": "Service is healthy or degraded"},
        500: {"model": ErrorResponse, "description": "Health check failed unexpectedly"},
    },
)
async def health_check(gemini_service: GeminiService = Depends(get_gemini_service)) -> HealthCheckResponse:
    """Check connectivity to dependencies (e.g., Gemini) and report health."""
    deps = {}
    try:
        deps["gemini_api"] = "available" 
    except Exception as e:
        logger.exception("Gemini health check failed during endpoint call")
        deps["gemini_api"] = "unavailable"

    status = "healthy" if all(v == "available" for v in deps.values()) else "degraded"
    
    return HealthCheckResponse(
        status=status,
        version=settings.version,
        dependencies=deps,
        timestamp=datetime.utcnow(),
    )

@main_router.post(
    "/analyze",
    response_model=ReviewResponse,
    tags=["Sentiment Analysis"],
    summary="Analyze Customer Reviews",
    responses={
        200: {"description": "Analysis successful"},
        422: {"model": ErrorResponse, "description": "Validation error in request payload"},
        500: {"model": ErrorResponse, "description": "Internal server error during analysis"},
        502: {"model": ErrorResponse, "description": "Upstream service (e.g., LLM) error"},
    },
)

async def analyze_reviews(
    review_request: ReviewRequest,
    processor: ReviewProcessor = Depends(get_processor),
) -> ReviewResponse:
    """Analyze a batch of reviews and return their labels + sentiment."""
    start_time = time.time()
    
    review_texts = [r.review_text for r in review_request.reviews]
    review_ids   = [r.review_id  for r in review_request.reviews]
    
    logger.info(f"Received /analyze request for {len(review_texts)} reviews.")

        
    try:
        result = await processor.process_reviews(review_texts, review_ids)

        if not result.is_success():
            logger.error(f"Review processing failed: {result.error}")
            raise HTTPException(status_code=502, detail=f"Analysis backend error: {result.error}")

        response_data = result.value 

        elapsed = time.time() - start_time
        logger.info(f"Successfully processed {len(review_texts)} reviews in {elapsed:.2f}s")
        
        return response_data 

    except HTTPException: 
        raise
    except Exception as e:
        logger.exception("Unexpected error during /analyze request")
        raise HTTPException(status_code=500, detail="Internal server error")
    

async def validate_freshdesk_signature(request: Request, webhook_secret: Optional[str]) -> bool:
    """
    Validates the signature of incoming Freshdesk webhooks.
    
    Freshdesk signs webhooks using HMAC-SHA256 with a shared secret.
    The signature is sent in the X-Freshdesk-Signature header.
    
    Args:
        request: The incoming request with headers and body
        webhook_secret: The shared secret configured in Freshdesk
        
    Returns:
        bool: True if signature is valid or if no secret is configured (development mode)
    """
    if not webhook_secret:
        logger.warning("Webhook signature validation skipped: No webhook_secret configured")
        return True
    
    try:
        # Get the signature from the header
        received_signature = request.headers.get("X-Freshdesk-Signature")
        if not received_signature:
            logger.warning("No X-Freshdesk-Signature header found")
            return False
            
        # Get the raw request body
        body = await request.body()
        
        # Calculate the expected signature
        import hmac
        import hashlib
        calculated_signature = hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures using constant-time comparison
        is_valid = hmac.compare_digest(calculated_signature, received_signature)
        
        if not is_valid:
            logger.warning("Invalid webhook signature")
        
        return is_valid
        
    except Exception as e:
        logger.exception(f"Error validating webhook signature: {str(e)}")
        return False


def convert_freshdesk_payload(raw_payload: Dict[str, Any]) -> FreshdeskWebhookPayload:
    """
    Converts raw Freshdesk webhook payload to the expected FreshdeskWebhookPayload structure.
    
    Handles both the native Freshdesk webhook format and the template format:
    {"reviews": [{"review_id": "{{ticket.id}}", "review_text": "{{ticket.description}}"}]}
    
    Args:
        raw_payload: The raw webhook payload from Freshdesk
        
    Returns:
        FreshdeskWebhookPayload: Structured payload for processing
    """
    # If payload already matches our expected structure, use it directly
    if "reviews" in raw_payload and isinstance(raw_payload["reviews"], list):
        try:
            return FreshdeskWebhookPayload.model_validate(raw_payload)
        except Exception as e:
            logger.warning(f"Payload has 'reviews' key but validation failed: {str(e)}")
    
    # Extract ticket info from standard Freshdesk webhook format
    ticket_data = {}
    
    # Try different possible structures from Freshdesk
    if "freshdesk_webhook" in raw_payload and "ticket" in raw_payload["freshdesk_webhook"]:
        # Format: {"freshdesk_webhook": {"ticket": {...}}}
        ticket_data = raw_payload["freshdesk_webhook"]["ticket"]
    elif "data" in raw_payload and "ticket" in raw_payload["data"]:
        # Format: {"data": {"ticket": {...}}}
        ticket_data = raw_payload["data"]["ticket"]
    elif "ticket" in raw_payload:
        # Format: {"ticket": {...}}
        ticket_data = raw_payload["ticket"]
    else:
        # Assume the entire payload is the ticket data
        ticket_data = raw_payload
    
    # Extract ticket ID and description
    ticket_id = None
    description = None
    
    if isinstance(ticket_data, dict):
        ticket_id = ticket_data.get("id")
        description = ticket_data.get("description", "")
    
    if not ticket_id:
        raise ValueError("Could not extract ticket ID from webhook payload")
    
    # Create our expected structure
    return FreshdeskWebhookPayload(
        reviews=[{
            "review_id": int(ticket_id),
            "review_text": description
        }]
    )

@main_router.post(
    "/webhook/freshdesk",
    summary="Handle Freshdesk Webhooks",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Integrations"]
)
async def handle_freshdesk_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    freshdesk_service: FreshdeskService = Depends(get_freshdesk_service),
    processor: ReviewProcessor = Depends(get_processor),
):
    """
    Automatically processes new tickets created in Freshdesk.
    The webhook is triggered by Freshdesk when tickets are created.
    """
    # Check if Freshdesk service is available
    if freshdesk_service is None:
        logger.error("Freshdesk webhook received, but Freshdesk service is not configured.")
        raise HTTPException(status_code=503, detail="Freshdesk integration is not configured")
    
    try:
        # Get the raw payload from Freshdesk
        raw_payload = await request.json()
        logger.info(f"Received webhook from Freshdesk: {json.dumps(raw_payload)[:200]}...")
        
        # Extract the ticket ID and description
        ticket_id = None
        description = None
        
        # Handle the payload format based on what Freshdesk sends
        if "reviews" in raw_payload and isinstance(raw_payload["reviews"], list) and raw_payload["reviews"]:
            # Our expected format from the webhook configuration
            review_item = raw_payload["reviews"][0]
            ticket_id = review_item.get("review_id")
            description = review_item.get("review_text")
        elif "freshdesk_webhook" in raw_payload and "ticket" in raw_payload["freshdesk_webhook"]:
            # Standard Freshdesk webhook format
            ticket_data = raw_payload["freshdesk_webhook"]["ticket"]
            ticket_id = ticket_data.get("id")
            description = ticket_data.get("description")
        elif "data" in raw_payload and "ticket" in raw_payload["data"]:
            # Alternative Freshdesk format
            ticket_data = raw_payload["data"]["ticket"]
            ticket_id = ticket_data.get("id")
            description = ticket_data.get("description")
        
        if not ticket_id:
            logger.error("Could not extract ticket ID from webhook payload")
            raise HTTPException(status_code=422, detail="Invalid webhook payload: missing ticket ID")
        
        logger.info(f"Extracted ticket ID {ticket_id} from webhook")
        
        # Create the payload structure expected by FreshdeskService
        webhook_payload = FreshdeskWebhookPayload(
            reviews=[{
                "review_id": int(ticket_id) if isinstance(ticket_id, str) and ticket_id.isdigit() else ticket_id,
                "review_text": description or ""
            }]
        )
        
        # Process the ticket in the background to avoid webhook timeout
        background_tasks.add_task(
            freshdesk_service.handle_webhook_event,
            processor=processor,
            payload=webhook_payload
        )
        
        # Return success immediately
        return {"message": f"Processing ticket {ticket_id} in background"}
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.exception(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")
