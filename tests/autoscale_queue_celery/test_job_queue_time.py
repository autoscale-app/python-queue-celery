import os
from datetime import datetime, timedelta, timezone

import pytest
from celery import Celery
from freezegun import freeze_time
from redis import ConnectionError, Redis

from autoscale_queue_celery import job_queue_time

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")

app = Celery("python_queue_celery", broker=REDIS_URL)


@app.task
def add(x, y):
    return x + y


@pytest.fixture(scope="module")
def redis_connection():
    return Redis.from_url(REDIS_URL)


@pytest.fixture(scope="function")
def clean_redis(redis_connection):
    redis_connection.flushdb()


def test_job_queue_time_invalid_redis_connection():
    with pytest.raises(ConnectionError):
        job_queue_time(["celery"], "redis://invalid-host:6379/0")


def test_job_queue_time_no_queues(redis_connection, clean_redis):
    with pytest.raises(ValueError, match="At least one queue must be provided"):
        job_queue_time([], REDIS_URL)


def test_job_queue_time_no_tasks(redis_connection, clean_redis):
    assert job_queue_time(["celery"], REDIS_URL) == 0


@freeze_time("2000-01-01")
def test_job_queue_time_one_task(redis_connection, clean_redis):
    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=5)):
        add.delay(1, 2)

    assert job_queue_time(["celery"], REDIS_URL) == 5.0


@freeze_time("2000-01-01")
def test_job_queue_time_multiple_tasks(redis_connection, clean_redis):
    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=10)):
        add.apply_async(args=[1, 2])

    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=5)):
        add.apply_async(args=[3, 4])

    assert job_queue_time(["celery"], REDIS_URL) == 10


@freeze_time("2000-01-01")
def test_job_queue_time_custom_queues(redis_connection, clean_redis):
    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=5)):
        add.apply_async(args=[1, 2])

    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=10)):
        add.apply_async(args=[3, 4], queue="celery_2")

    assert job_queue_time(["celery", "celery_2"], REDIS_URL) == 10


@freeze_time("2000-01-01")
def test_job_queue_time_eta(redis_connection, clean_redis):
    eta = datetime.now(timezone.utc) + timedelta(seconds=5)
    add.apply_async(args=[1, 2], eta=eta)
    assert job_queue_time(["celery"], REDIS_URL) == 0


@freeze_time("2000-01-01")
def test_job_queue_time_eta_passed(redis_connection, clean_redis):
    eta = datetime.now(timezone.utc) - timedelta(seconds=5)
    add.apply_async(args=[1, 2], eta=eta)
    assert job_queue_time(["celery"], REDIS_URL) == 5


@freeze_time("2000-01-01")
def test_job_queue_time_countdown(redis_connection, clean_redis):
    add.apply_async(args=[1, 2], countdown=5)
    assert job_queue_time(["celery"], REDIS_URL) == 0


@freeze_time("2000-01-01")
def test_job_queue_time_countdown_passed(redis_connection, clean_redis):
    add.apply_async(args=[1, 2], countdown=-5)
    assert job_queue_time(["celery"], REDIS_URL) == 5


@freeze_time("2000-01-01")
def test_job_queue_time_expiration(redis_connection, clean_redis):
    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=60)):
        expired = datetime.now(timezone.utc) + timedelta(seconds=30)
        add.apply_async(args=[1, 2], expires=expired)

    with freeze_time(datetime.now(timezone.utc) - timedelta(seconds=30)):
        add.apply_async(args=[3, 4])

    assert job_queue_time(["celery"], REDIS_URL) == 0


def test_job_queue_time_redis_url_from_env_var(
    monkeypatch, redis_connection, clean_redis
):
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    assert job_queue_time(["celery"]) == 0


def test_job_queue_time_no_redis_url(monkeypatch, redis_connection, clean_redis):
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(
        ValueError,
        match="redis_url not provided and REDIS_URL environment variable is not set",
    ):
        job_queue_time(["celery"], None)


def test_job_queue_time_empty_redis_url(monkeypatch, redis_connection, clean_redis):
    monkeypatch.setenv("REDIS_URL", "")
    with pytest.raises(
        ValueError,
        match="redis_url not provided and REDIS_URL environment variable is not set",
    ):
        job_queue_time(["celery"], None)
