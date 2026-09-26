"""Background execution of analysis jobs.

Progress is stored in the database, so any backend instance can report it. This runner uses an in-process
thread pool; with several backend instances, replace `submit` with a shared queue (e.g. Redis + arq).
"""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, mode: str, workers: int):
        self.mode = mode
        self._executor = (
            ThreadPoolExecutor(max_workers=workers, thread_name_prefix="analysis") if mode == "thread" else None
        )

    def submit(self, fn: Callable[..., None], *args) -> None:
        if self._executor is None:
            fn(*args)
            return
        future = self._executor.submit(fn, *args)
        future.add_done_callback(self._log_failure)

    @staticmethod
    def _log_failure(future: Future) -> None:
        if (exc := future.exception()) is not None:
            logger.error("background job crashed", exc_info=exc)

    def shutdown(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=False)


_runner: JobRunner | None = None
_lock = threading.Lock()


def get_job_runner() -> JobRunner:
    global _runner
    with _lock:
        if _runner is None:
            settings = get_settings()
            _runner = JobRunner(settings.JOB_MODE, settings.JOB_WORKERS)
        return _runner


def shutdown_job_runner() -> None:
    global _runner
    with _lock:
        if _runner is not None:
            _runner.shutdown()
            _runner = None
