from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
import logging, time
from datetime import datetime

from customer_sentiment_hub.api.models import ReviewRequest, ReviewResponse, HealthCheckResponse
from customer_sentiment_hub.services.processor import ReviewProcessor
from customer_sentiment_hub.services.gemini_service import GeminiService
from customer_sentiment_hub.domain.validation import ValidationService
from customer_sentiment_hub.config.settings import settings

logger = logging.getLogger("customer_sentiment_hub")
# _major = settings.version.split(".")[0]
api_prefix = settings.api_version
# print(f"settings.api_version :: {settings.api_version}")
main_router = APIRouter(prefix=f"/{api_prefix}")


# --- Dependency Injection via FastAPI startup event ---
def get_processor(request: Request) -> ReviewProcessor:
    return request.app.state.processor

def get_gemini_service(request: Request) -> GeminiService:
    return request.app.state.gemini_service

def get_validation_service(request: Request) -> ValidationService:
    return request.app.state.validation_service

def create_app() -> FastAPI:
    app = FastAPI(title="Customer Sentiment Hub")

    # Instantiate shared services once
    validation = ValidationService()
    gemini = GeminiService(
        gemini_settings=settings.gemini,
        google_settings=settings.google_cloud,
        validation_service=validation,
    )
    processor = ReviewProcessor(
        llm_service=gemini,
        settings=settings.processing,
    )

    app.state.validation_service = validation
    app.state.gemini_service = gemini
    app.state.processor = processor

    # Include only the two live routes
    app.include_router(main_router)
    return app

app = create_app()


# Health check
@main_router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["System"],
)
async def health_check():
    """Check connectivity to Gemini and report health."""
    deps = {}
    try:
        await app.state.gemini_service.test_connection()
        deps["gemini_api"] = "available"
    except Exception:
        logger.exception("Gemini health check failed")
        deps["gemini_api"] = "unavailable"

    status = "healthy" if all(v == "available" for v in deps.values()) else "degraded"
    payload = {
        "status": status,
        "version": settings.version,
        "dependencies": deps,
        "timestamp": datetime.utcnow(),
    }
    # FastAPI auto-serializes datetime in ISO format
    return HealthCheckResponse(**payload)


# Main sentiment analysis
@main_router.post(
    "/analyze",
    response_model=ReviewResponse,
    tags=["Sentiment Analysis"],
)
async def analyze_reviews(
    review_request: ReviewRequest,
    processor: ReviewProcessor = Depends(get_processor),
):
    """Analyze a batch of reviews and return their labels + sentiment."""
    start = time.time()
    try:
        texts = [r.review_text for r in review_request.reviews]
        ids   = [r.review_id   for r in review_request.reviews]
        result = await processor.process_reviews(texts, ids)

        if not result.is_success():
            logger.error("Processing failed: %s", result.error)
            raise HTTPException(500, detail=result.error)

        elapsed = time.time() - start
        logger.info("Processed %d reviews in %.2f s", len(texts), elapsed)
        return ReviewResponse(reviews=result.value["reviews"])

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /analyze")
        raise HTTPException(500, detail="Internal server error")