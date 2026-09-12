#!/usr/bin/env python3
"""AttackSurface Production Supervisor.

Runs continuously outside Vercel, managing both the persistent RQ Worker and
persistent 10-Minute Scheduler with automatic restart recovery.

Architecture:
    Vercel (Web / API)
          ↓
    Upstash Redis (Queues: p0_critical, p1_official, p2_standard, ai, snapshots, etc.)
          ↓
    Persistent RQ Worker (app.worker)
          ↑
    Persistent 10-Min Scheduler (app.scheduler)
          ↓
    Collectors (ConnectorEngine, CISA KEV, Gemini AI)
          ↓
    Supabase PostgreSQL (aws-0-ap-northeast-1.pooler.supabase.com:6543)
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
API_DIR = ROOT_DIR / "api"
LOG_FILE = ROOT_DIR / "production_supervisor.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Supervisor] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("Supervisor")


class ProcessSupervisor:
    """Monitors and automatically recovers worker and scheduler processes."""

    def __init__(self):
        self.worker_proc: subprocess.Popen | None = None
        self.scheduler_proc: subprocess.Popen | None = None
        self.running = True
        self.restart_counts = {"worker": 0, "scheduler": 0}

    def _get_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(API_DIR)
        return env

    def start_worker(self) -> None:
        cmd = [sys.executable, "-m", "app.worker"]
        logger.info("Spawning persistent Worker process: %s", " ".join(cmd))
        worker_log = open(ROOT_DIR / "production_worker.log", "a", encoding="utf-8")
        self.worker_proc = subprocess.Popen(
            cmd,
            cwd=str(API_DIR),
            env=self._get_env(),
            stdout=worker_log,
            stderr=subprocess.STDOUT,
        )
        logger.info("Worker started (PID: %d)", self.worker_proc.pid)

    def start_scheduler(self) -> None:
        cmd = [sys.executable, "-m", "app.scheduler", "--interval", "600"]
        logger.info("Spawning persistent 10-Minute Scheduler process: %s", " ".join(cmd))
        scheduler_log = open(ROOT_DIR / "production_scheduler.log", "a", encoding="utf-8")
        self.scheduler_proc = subprocess.Popen(
            cmd,
            cwd=str(API_DIR),
            env=self._get_env(),
            stdout=scheduler_log,
            stderr=subprocess.STDOUT,
        )
        logger.info("Scheduler started (PID: %d)", self.scheduler_proc.pid)

    def stop_all(self) -> None:
        self.running = False
        logger.info("Stopping all supervised processes...")
        for name, proc in [("Worker", self.worker_proc), ("Scheduler", self.scheduler_proc)]:
            if proc and proc.poll() is None:
                logger.info("Terminating %s (PID: %d)...", name, proc.pid)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        logger.info("All processes stopped.")

    def supervise_loop(self) -> None:
        logger.info("=" * 80)
        logger.info("AttackSurface Production Supervisor Initialized")
        logger.info("Target Database: Supabase PostgreSQL (Managed)")
        logger.info("Target Queue: Upstash Redis (TLS / rediss://)")
        logger.info("Cycle Interval: 600 seconds (10 minutes)")
        logger.info("=" * 80)

        self.start_worker()
        self.start_scheduler()

        while self.running:
            time.sleep(2)

            # Check worker status
            if self.worker_proc and self.worker_proc.poll() is not None:
                exit_code = self.worker_proc.returncode
                self.restart_counts["worker"] += 1
                logger.warning(
                    "[AUTOMATIC RESTART RECOVERY] Worker (PID: %d) exited with code %d. Restarting (#%d)...",
                    self.worker_proc.pid,
                    exit_code,
                    self.restart_counts["worker"],
                )
                time.sleep(1)
                self.start_worker()

            # Check scheduler status
            if self.scheduler_proc and self.scheduler_proc.poll() is not None:
                exit_code = self.scheduler_proc.returncode
                self.restart_counts["scheduler"] += 1
                logger.warning(
                    "[AUTOMATIC RESTART RECOVERY] Scheduler (PID: %d) exited with code %d. Restarting (#%d)...",
                    self.scheduler_proc.pid,
                    exit_code,
                    self.restart_counts["scheduler"],
                )
                time.sleep(1)
                self.start_scheduler()


def main():
    supervisor = ProcessSupervisor()

    def handle_signal(sig, frame):
        logger.info("Received signal %s; shutting down...", sig)
        supervisor.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        supervisor.supervise_loop()
    except KeyboardInterrupt:
        supervisor.stop_all()


if __name__ == "__main__":
    main()
