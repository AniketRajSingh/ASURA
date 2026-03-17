# ============================================================
# core/utils/retry.py — Transient Error Handling (Retry)
# ============================================================

import time
import asyncio
import functools
import traceback
from typing import Callable, Type, Tuple, Any, Coroutine

from settings import settings as config
from skills.logger import log_audit, log_app


def retry(
    *,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """
    Generic synchronous retry decorator.
    """
    if backoff < 1.0:
        raise ValueError("backoff multiplier must be >= 1.0")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt <= retries:
                try:
                    result = func(*args, **kwargs)
                    return result
                except exceptions as exc:
                    attempt += 1
                    if attempt > retries:
                        log_audit("RETRY_FAIL", f"{func.__name__} failed after {retries} retries: {exc}")
                        raise
                    log_app(f"Retry {attempt}/{retries} for {func.__name__} in {current_delay}s")
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator


def async_retry(
    *,
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """
    Asynchronous retry decorator for coroutines.
    """
    if backoff < 1.0:
        raise ValueError("backoff multiplier must be >= 1.0")

    def decorator(func: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt <= retries:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    attempt += 1
                    if attempt > retries:
                        log_audit("RETRY_FAIL_ASYNC", f"{func.__name__} failed after {retries} retries: {exc}")
                        raise
                    log_app(f"Async Retry {attempt}/{retries} for {func.__name__} in {current_delay}s")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

__all__ = ["retry", "async_retry"]
