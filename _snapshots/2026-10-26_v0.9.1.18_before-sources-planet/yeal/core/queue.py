"""Thread-based download queue with a bounded number of parallel jobs."""
from __future__ import annotations

import itertools
import threading
import time
from collections import deque
from dataclasses import replace
from typing import Callable, Dict, List, Optional

from .models import DownloadJob, DownloadOptions, JobState

MAX_WORKERS = 4


RATE_LIMIT_PAUSE = 90   # seconds without new downloads after a rate-limit / bot-check answer


def rate_limited(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in ("429", "too many requests", "not a bot", "rate-limit", "rate limit"))


class DownloadQueue:
    """`runner(job, cancel_event, notify)` executes one job (see Engine.run).

    Callbacks are invoked from worker threads with *snapshots* of the job, so
    the UI layer only has to marshal them onto its own thread.
    """

    def __init__(self, runner: Callable, max_parallel: int = 2,
                 on_change: Optional[Callable[[DownloadJob], None]] = None,
                 on_remove: Optional[Callable[[int], None]] = None):
        self._runner = runner
        self._max = max(1, min(MAX_WORKERS, max_parallel))
        self._on_change = on_change or (lambda job: None)
        self._on_remove = on_remove or (lambda job_id: None)
        self._ids = itertools.count(1)
        self._jobs: Dict[int, DownloadJob] = {}
        self._events: Dict[int, threading.Event] = {}
        self._pending: deque = deque()
        self._running = 0
        self._stop = False
        self._cooldown_until = 0.0     # no new job starts before this time (rate limit hit)
        self._cond = threading.Condition()
        self._workers = [threading.Thread(target=self._worker, name=f"yeal-dl-{i}", daemon=True)
                         for i in range(MAX_WORKERS)]
        for w in self._workers:
            w.start()

    # ---- public API -----------------------------------------------------
    def add(self, url: str, options: DownloadOptions) -> DownloadJob:
        with self._cond:
            job = DownloadJob(next(self._ids), url.strip(), options.normalized())
            self._jobs[job.id] = job
            self._events[job.id] = threading.Event()
            self._pending.append(job.id)
            self._cond.notify_all()
        self._emit(job)
        return job

    def restore(self, jobs: List[DownloadJob]) -> None:
        """Put finished jobs from the history into the list (they can be retried or removed)."""
        for job in jobs:
            with self._cond:
                job.id = next(self._ids)
                self._jobs[job.id] = job
                self._events[job.id] = threading.Event()
            self._emit(job)

    def cancel(self, job_id: int) -> None:
        with self._cond:
            job = self._jobs.get(job_id)
            if job is None or job.state.finished:
                return
            self._events[job_id].set()
            if job_id in self._pending:           # not started yet
                self._pending.remove(job_id)
                job.state = JobState.CANCELED
            else:
                return                             # running: engine reports CANCELED
        self._emit(job)

    def retry(self, job_id: int) -> None:
        with self._cond:
            job = self._jobs.get(job_id)
            if job is None or not job.state.finished or job.state is JobState.DONE:
                return
            job.reset()
            self._events[job_id] = threading.Event()
            self._pending.append(job_id)
            self._cond.notify_all()
        self._emit(job)

    def remove(self, job_id: int) -> None:
        self.cancel(job_id)
        with self._cond:
            job = self._jobs.get(job_id)
            if job is None or not job.state.finished:
                return  # unknown, or a running job still winding down
            self._jobs.pop(job_id, None)
            self._events.pop(job_id, None)
        self._on_remove(job_id)

    def clear_finished(self) -> None:
        for job in self.jobs():
            if job.state.finished:
                self.remove(job.id)

    def set_max_parallel(self, n: int) -> None:
        with self._cond:
            self._max = max(1, min(MAX_WORKERS, int(n)))
            self._cond.notify_all()

    def jobs(self) -> List[DownloadJob]:
        with self._cond:
            return [replace(j) for j in self._jobs.values()]

    def shutdown(self) -> None:
        with self._cond:
            self._stop = True
            for ev in self._events.values():
                ev.set()
            self._cond.notify_all()

    # ---- internals ------------------------------------------------------
    def _emit(self, job: DownloadJob) -> None:
        self._on_change(replace(job))

    def _worker(self) -> None:
        while True:
            with self._cond:
                while True:
                    wait = self._cooldown_until - time.time()
                    if self._stop or (self._pending and self._running < self._max and wait <= 0):
                        break
                    self._cond.wait(timeout=wait if wait > 0 and self._pending else None)
                if self._stop:
                    return
                job_id = self._pending.popleft()
                job = self._jobs.get(job_id)
                if job is None or job.state.finished:
                    continue
                cancel = self._events[job_id]
                self._running += 1
            try:
                self._runner(job, cancel, self._emit)
            except Exception as exc:  # noqa: BLE001 - a runner bug must not kill the worker
                job.state = JobState.ERROR
                job.error = str(exc)[:300]
                self._emit(job)
            finally:
                with self._cond:
                    self._running -= 1
                    self._cond.notify_all()
            if job.state == JobState.ERROR and rate_limited(job.error):
                with self._cond:   # YouTube asked us to slow down: pause the whole queue
                    self._cooldown_until = time.time() + RATE_LIMIT_PAUSE
                job.error += f"  (queue paused {RATE_LIMIT_PAUSE} s)"
                self._emit(job)
