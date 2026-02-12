import time
import json
import logging
from functools import wraps

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("nyx-observer")

def measure_latency(component_name: str):
    """
    A decorator factory to measure and log the execution latency of asynchronous functions.

    This utility wraps the target function to capture start and end times, calculating
    the duration in milliseconds. It emits a structured JSON log entry containing the
    component name, latency, and execution status (success/error).

    Args:
        component_name (str): A unique label to identify the component being measured 
                              in the logs (e.g., 'rag_pipeline', 'embedding_generation').

    Returns:
        Callable: The decorated function with added timing and logging instrumentation.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise e
            finally:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                
                log_payload = {
                    "event": "performance_metric",
                    "component": component_name,
                    "latency_ms": round(latency_ms, 2),
                    "status": status
                }
                # Log as valid JSON string
                logger.info(json.dumps(log_payload))
        return wrapper
    return decorator