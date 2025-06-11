from functools import wraps
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException, status


logger = logging.getLogger(__name__)

thread_pool = ThreadPoolExecutor(max_workers=10)  # Limit concurrent retries
active_threads = {}  # Track running threads to avoid duplicate retries


def retry_async_on_failure(max_retries=3, sleep_times=[1, 2, 4]):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            thread_key = threading.get_ident()

            try:
                logger.info(f"Initial attempt in threadId: {threading.get_ident()}")
                return func(*args, **kwargs)
            except HTTPException as e:
                logger.error(f"Initial attempt failed with error: {e.detail}")

                def retry_logic():
                    attempts = 0
                    while attempts < max_retries:
                        try:
                            logger.info(
                                f"Retrying in threadId: {threading.get_ident()}"
                            )
                            result = func(*args, **kwargs)
                            del active_threads[thread_key]
                            return result
                        except HTTPException as e:
                            logger.error(f"Attempt {attempts + 1} failed: {e.detail}")
                            if attempts < max_retries - 1:
                                sleep_time = sleep_times[attempts]
                                logger.info(f"Retrying in {sleep_time} seconds...")
                                time.sleep(sleep_time)
                            attempts += 1
                    logger.error("All retries failed.")
                    del active_threads[thread_key]

                if thread_key not in active_threads:
                    future = thread_pool.submit(retry_logic)
                    active_threads[thread_key] = future

        return wrapper

    return decorator
