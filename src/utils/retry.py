"""
Utility functions for retrying API calls with exponential backoff
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional

logger = logging.getLogger(__name__)


def retry_on_exception(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True
):
    """
    Decorator to retry a function on specific exceptions with exponential backoff

    Args:
        exceptions: Tuple of exception types to catch
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (delay = backoff_factor * (2 ** attempt))
        max_delay: Maximum delay between retries in seconds
        jitter: If True, add random jitter to delay to prevent thundering herd

    Example:
        @retry_on_exception((requests.RequestException,), max_retries=3)
        def fetch_data():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import random

            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        # Final attempt failed
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        backoff_factor * (2 ** attempt),
                        max_delay
                    )

                    # Add jitter to prevent synchronized retries
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


class RetryableAPIError(Exception):
    """Base exception for retryable API errors"""
    pass


class APIClient:
    """
    Wrapper for requests session with built-in retry logic

    Example:
        client = APIClient(max_retries=3)
        response = client.get("https://api.example.com/data")
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 30.0
    ):
        import requests

        self.session = requests.Session()
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.timeout = timeout

    def get(self, url: str, **kwargs) -> 'requests.Response':
        """GET request with retry logic"""
        return self._request_with_retry('GET', url, **kwargs)

    def post(self, url: str, **kwargs) -> 'requests.Response':
        """POST request with retry logic"""
        return self._request_with_retry('POST', url, **kwargs)

    def _request_with_retry(self, method: str, url: str, **kwargs):
        """Execute request with retry logic"""
        import random
        import requests

        kwargs.setdefault('timeout', self.timeout)

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                if attempt == self.max_retries:
                    logger.error(f"Request to {url} failed after {self.max_retries} retries: {e}")
                    raise

                # Calculate delay with exponential backoff
                delay = min(
                    self.backoff_factor * (2 ** attempt),
                    self.max_delay
                )

                # Add jitter
                delay = delay * (0.5 + random.random())

                logger.warning(
                    f"Request to {url} failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)

    def close(self):
        """Close the session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
