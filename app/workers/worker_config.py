"""
ARQ Worker Configuration

This file defines the worker settings and task functions that ARQ will run.

To start workers:
    arq app.workers.worker_config.WorkerSettings
"""
import os
from dotenv import load_dotenv
from arq.connections import RedisSettings

# Load environment variables
load_dotenv()

from app.workers.media_tasks import (
    generate_thumbnail,
    optimize_image,
    process_media,
)
from app.workers.email_tasks import (
    send_single_email,
    send_bulk_emails,
)


class WorkerSettings:
    """
    ARQ Worker Settings

    Docs: https://arq-docs.helpmanual.io/
    """

    # Redis connection
    redis_settings = RedisSettings(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        database=int(os.getenv('REDIS_DB', '0')),
        password=os.getenv('REDIS_PASSWORD') or None,
    )

    # Task functions
    functions = [
        # Media processing tasks
        generate_thumbnail,
        optimize_image,
        process_media,

        # Email tasks
        send_single_email,
        send_bulk_emails,
    ]

    # Worker configuration
    queue_name = 'arq:queue'  # Default queue name
    max_jobs = 10  # Maximum number of concurrent jobs per worker
    job_timeout = 300  # Job timeout in seconds (5 minutes)
    keep_result = 3600  # Keep job results for 1 hour

    # Retry configuration
    max_tries = 3  # Maximum number of retries
    retry_jobs = True  # Enable automatic retry on failure

    # Worker health check
    health_check_interval = 60  # Check worker health every 60 seconds

    # Logging
    log_results = True  # Log job results

    # Job serialization
    job_serializer = None  # Use default (pickle)
    job_deserializer = None


# For starting worker with: arq app.workers.worker_config.WorkerSettings
