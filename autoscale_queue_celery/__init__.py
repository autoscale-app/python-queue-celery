import os
from datetime import datetime, timezone

from celery import signals
from kombu.serialization import loads
from redis import Redis

__version__ = "0.2.0"
__author__ = "Michael R. van Rooijen"
__contact__ = "support@autoscale.app"
__homepage__ = "https://autoscale.app"
__docformat__ = "restructuredtext"
__keywords__ = "python queue worker autoscale celery"


def job_queue_time(queue_names, redis_url=None):
    """
    Calculates the maximum job queue time across multiple queues in Redis.

    Parameters:
    - queue_names (list): A list of queue names to query.
    - redis_url (str): A Redis connection URL. If not provided, the REDIS_URL environment variable
        will be used. If the environment variable is not set, a ValueError will be raised.

    Returns:
    - The maximum job queue time (float) in seconds across all the provided queues. Returns 0 if no tasks can be found.

    This function retrieves the tail of the queue (the task that would be processed next by a worker)
    for each provided queue name using a single Redis transaction, and then calculates the job queue time
    of the tail task for each queue, taking into account the 'eta', 'expires', and 'enqueued_at'
    timestamp attributes. The maximum job queue time across all the provided queues is then returned.

    If a task has an 'expires' attribute, it checks whether the task has expired. If it has, the task
    is skipped, and its job queue time is not considered. If the task has an 'eta' attribute and the current
    time is greater than or equal to the 'eta', the job queue time is calculated as the difference between
    the current time and 'eta'. If the task does not have an 'eta' attribute, the job queue time is calculated
    as the difference between the current time and 'enqueued_at'.

    The enqueued_at header is added to each task before it's sent to the broker using the
    'add_enqueued_at_header' function. It is not added by default by Celery, so this function must be
    called before any tasks are sent to the broker.
    """
    if not queue_names:
        raise ValueError("At least one queue must be provided")

    if not redis_url:
        redis_url = os.environ.get("REDIS_URL")

    if not redis_url:
        raise ValueError(
            "redis_url not provided and REDIS_URL environment variable is not set"
        )

    redis_conn = Redis.from_url(redis_url)

    try:
        with redis_conn.pipeline(transaction=True) as pipe:
            for queue_name in queue_names:
                pipe.lindex(queue_name, -1)

            serialized_tasks = pipe.execute()

        max_job_queue_time = 0

        for serialized_task in serialized_tasks:
            if serialized_task:
                task = loads(
                    serialized_task,
                    content_type="application/json",
                    content_encoding="utf-8",
                )
                current_time = datetime.now(timezone.utc)
                job_queue_time_seconds = 0

                if task["headers"]["expires"]:
                    expires_time = datetime.fromisoformat(
                        task["headers"]["expires"]
                    ).replace(tzinfo=timezone.utc)
                    if current_time >= expires_time:
                        continue

                if task["headers"]["eta"]:
                    eta_time = datetime.fromisoformat(task["headers"]["eta"]).replace(
                        tzinfo=timezone.utc
                    )
                    if current_time >= eta_time:
                        job_queue_time_seconds = (
                            current_time - eta_time
                        ).total_seconds()
                else:
                    enqueued_at = datetime.fromisoformat(task["headers"]["enqueued_at"])
                    job_queue_time_seconds = (
                        current_time - enqueued_at
                    ).total_seconds()

                if job_queue_time_seconds > max_job_queue_time:
                    max_job_queue_time = job_queue_time_seconds

        return max_job_queue_time
    finally:
        redis_conn.connection_pool.disconnect()


@signals.before_task_publish.connect
def add_enqueued_at_header(sender=None, headers=None, **kwargs):
    """
    Add an 'enqueued_at' header to each task before it's sent.
    """
    headers["enqueued_at"] = datetime.now(timezone.utc).isoformat()
