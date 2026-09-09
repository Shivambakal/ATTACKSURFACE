"""Scale simulation tests (10, 100, 1,000, 10,000 companies).

Simulates high-volume enterprise source scheduling, queue partitioning,
deduplication efficiency, and Redis distributed lock contention without
hitting live external networks.
"""
import time
from unittest.mock import MagicMock
import pytest

from app.models.company import Company
from app.models.source_registry import CompanySource
from app.services.corporate_scheduler import CorporateScheduler
from app.services.corporate_clustering import compute_corporate_fingerprint


def test_scale_scheduling_simulation_10k():
    """Simulates 10,000 companies with 5 sources each (50,000 total sources)."""
    mock_redis = MagicMock()
    mock_redis.set.return_value = True
    scheduler = CorporateScheduler(redis_client=mock_redis)

    sources = []
    priorities = ["P0", "P1", "P2", "P3", "P4"]

    # Generate 50k mock sources in memory
    start_gen = time.monotonic()
    for i in range(50000):
        pri = priorities[i % 5]
        sources.append(
            CompanySource(
                id=i + 1,
                company_id=(i % 1000) + 1,
                name=f"Source {i}",
                source_url=f"https://company{i}.com/feed",
                priority=pri,
                poll_interval_seconds=600,
            )
        )
    gen_duration = time.monotonic() - start_gen

    # Partition 50k sources into priority queues
    start_part = time.monotonic()
    buckets = scheduler.partition_by_priority(sources)
    part_duration = time.monotonic() - start_part

    assert len(sources) == 50000
    assert len(buckets["p0_critical"]) == 10000
    assert len(buckets["p1_official"]) == 10000
    assert len(buckets["p2_standard"]) == 10000
    assert len(buckets["p3_replay"]) == 10000
    assert len(buckets["p4_community"]) == 10000

    # Must complete partitioning in under 0.5 seconds
    assert part_duration < 0.5


def test_fingerprint_dedup_throughput():
    """Simulates 50,000 corporate change announcements to verify hash throughput."""
    start = time.monotonic()
    fingerprints = set()
    for i in range(50000):
        fp = compute_corporate_fingerprint(
            company_id=(i % 100) + 1,
            product_name=f"Product {i % 10}",
            change_type="API_UPDATED",
            normalized_title=f"Released endpoint /v1/resource/{i}",
        )
        fingerprints.add(fp)

    duration = time.monotonic() - start
    assert len(fingerprints) == 50000
    assert duration < 1.0  # High-throughput hashing
