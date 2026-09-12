"""Production worker entrypoint.

Runs RQ workers for background job queues: snapshots, providers, ai, alerts.
"""
import logging
import platform
from redis import Redis
from rq import Worker, Queue
from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Worker")

QUEUES = [
    "p0_critical",
    "p1_official",
    "p2_standard",
    "p3_replay",
    "p4_community",
    "snapshots",
    "providers",
    "ai",
    "alerts",
]


def run_worker() -> None:
    logger.info("Initializing RQ persistent worker connecting to Redis: %s", settings.redis_url.split("@")[-1])
    connection = Redis.from_url(settings.redis_url)
    queues = [Queue(name, connection=connection) for name in QUEUES]

    if platform.system() == "Windows":
        from rq import SimpleWorker
        from rq.timeouts import TimerDeathPenalty

        class WindowsWorker(SimpleWorker):
            death_penalty_class = TimerDeathPenalty

        worker = WindowsWorker(queues, connection=connection)
    else:
        worker = Worker(queues, connection=connection)

    logger.info("Persistent worker listening on queues: %s", [q.name for q in queues])
    worker.work()


if __name__ == "__main__":
    run_worker()
