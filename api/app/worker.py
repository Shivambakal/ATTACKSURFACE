"""Production worker entrypoint.

Runs RQ workers for background job queues: snapshots, providers, ai, alerts.
"""
from redis import Redis
from rq import Worker, Queue
from .config import settings

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

if __name__ == "__main__":
    connection = Redis.from_url(settings.redis_url)
    queues = [Queue(name, connection=connection) for name in QUEUES]
    Worker(queues, connection=connection).work()
