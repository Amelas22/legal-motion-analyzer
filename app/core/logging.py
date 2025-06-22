import logging
import sys
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        logging.info(
            f"Request completed - {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.4f}s - ID: {request_id}"
        )
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response