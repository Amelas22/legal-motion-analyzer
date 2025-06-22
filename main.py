from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import time
import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from app.core.config import settings
from app.models.schemas import (
    MotionAnalysisRequest, 
    ComprehensiveMotionAnalysisResponse, 
    HealthCheck,
    ArgumentCategory
)
from app.services.motion_analyzer import MotionAnalyzer
from app.core.security import SecurityHeadersMiddleware
from app.core.logging import setup_logging, LoggingMiddleware
from app.core.rate_limiting import RateLimitMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize motion analyzer
motion_analyzer = MotionAnalyzer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Legal Motion Analysis API v2.0")
    await motion_analyzer.initialize()
    yield
    # Shutdown
    logger.info("Shutting down Legal Motion Analysis API")
    await motion_analyzer.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Legal Motion Analysis API",
    description="Production-ready API for comprehensive analysis of legal motions - extracts ALL arguments",
    version="2.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

# Trusted hosts
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID", "X-Processing-Time"]
)

# Security
security = HTTPBearer(auto_error=False)

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Basic health check endpoint"""
    return HealthCheck(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="2.0.0"
    )

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with dependencies"""
    health_status = {
        "status": "healthy",
        "checks": {},
        "timestamp": datetime.utcnow(),
        "version": "2.0.0"
    }
    
    # Check motion analyzer
    try:
        await motion_analyzer.health_check()
        health_status["checks"]["motion_analyzer"] = "healthy"
    except Exception as e:
        health_status["checks"]["motion_analyzer"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

@app.post(f"{settings.API_V1_STR}/analyze-motion", response_model=ComprehensiveMotionAnalysisResponse)
async def analyze_motion(
    request: MotionAnalysisRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(security)
):
    """
    Comprehensive motion analysis that extracts ALL arguments
    
    This endpoint:
    - Extracts EVERY argument from the motion, no matter how minor
    - Categorizes arguments flexibly (can create custom categories)
    - Groups related arguments strategically
    - Identifies themes, patterns, and missing arguments
    - Provides detailed response strategy recommendations
    - Validates all legal citations
    """
    try:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Starting comprehensive motion analysis", extra={"request_id": request_id})
        
        # Analyze motion
        result = await motion_analyzer.analyze_motion(
            motion_text=request.motion_text,
            case_context=request.case_context,
            analysis_options=request.analysis_options
        )
        
        processing_time = time.time() - start_time
        
        # Log completion with summary
        logger.info(
            f"Motion analysis completed",
            extra={
                "request_id": request_id,
                "processing_time": processing_time,
                "motion_type": result.motion_type,
                "total_arguments": result.total_arguments_found,
                "categories_used": len(result.categories_used),
                "custom_categories": len(result.custom_categories_created)
            }
        )
        
        return ComprehensiveMotionAnalysisResponse(
            **result.model_dump(),
            request_id=request_id,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Motion analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.get(f"{settings.API_V1_STR}/argument-categories")
async def get_argument_categories():
    """Get all available argument categories"""
    categories = {}
    
    # Group by type
    category_groups = {
        "negligence": [],
        "liability": [],
        "causation": [],
        "damages": [],
        "procedural": [],
        "evidence": [],
        "expert": [],
        "other": []
    }
    
    for cat in ArgumentCategory:
        cat_value = cat.value
        cat_name = cat_value.replace("_", " ").title()
        
        # Determine group
        if cat_value.startswith("negligence_"):
            category_groups["negligence"].append({"value": cat_value, "name": cat_name})
        elif cat_value.startswith("liability_"):
            category_groups["liability"].append({"value": cat_value, "name": cat_name})
        elif cat_value.startswith("causation_"):
            category_groups["causation"].append({"value": cat_value, "name": cat_name})
        elif cat_value.startswith("damages_"):
            category_groups["damages"].append({"value": cat_value, "name": cat_name})
        elif cat_value.startswith("procedural_"):
            category_groups["procedural"].append({"value": cat_value, "name": cat_name})
        elif cat_value.startswith("evidence_"):
            category_groups["evidence"].append({"value": cat_value, "name": cat_name})
        elif cat_value.startswith("expert_"):
            category_groups["expert"].append({"value": cat_value, "name": cat_name})
        else:
            category_groups["other"].append({"value": cat_value, "name": cat_name})
    
    return {
        "categories": category_groups,
        "total_categories": len(list(ArgumentCategory)),
        "note": "AI can create custom categories beyond these predefined ones"
    }

@app.get(f"{settings.API_V1_STR}/motion-types")
async def get_motion_types():
    """Get supported motion types"""
    return {
        "motion_types": [
            "Motion to Dismiss",
            "Motion for Summary Judgment", 
            "Motion in Limine",
            "Motion to Compel",
            "Motion for Protective Order",
            "Motion to Exclude Expert",
            "Motion for Sanctions",
            "Discovery Motion",
            "Jurisdictional Motion",
            "Other"
        ],
        "note": "System can handle any motion type"
    }

@app.get(f"{settings.API_V1_STR}/analysis-stats")
async def get_analysis_stats():
    """Get statistics about the analysis capabilities"""
    return {
        "capabilities": {
            "max_motion_length": 50000,
            "min_motion_length": 100,
            "max_arguments_tracked": "unlimited",
            "citation_extraction": True,
            "custom_categories": True,
            "argument_grouping": True,
            "strategic_analysis": True
        },
        "version": "2.0.0",
        "improvements": [
            "Extracts ALL arguments, not just predefined categories",
            "Flexible categorization with custom category creation",
            "Groups related arguments strategically",
            "Identifies implied and missing arguments",
            "Provides comprehensive response strategy"
        ]
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "path": str(request.url)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )