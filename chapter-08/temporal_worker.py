#!/usr/bin/env python3
"""
Temporal Worker

Listens for workflow tasks and executes activities.
"""

import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from temporal_workflow import (
    PaginatedIngestionWorkflow,
    MonthlyReportWorkflow,
    fetch_api_page,
    transform_page,
    merge_pages,
    generate_report,
    publish_report
)


async def main():
    """Start Temporal worker."""
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")

    # Create worker
    worker = Worker(
        client,
        task_queue="etl-workers",
        workflows=[PaginatedIngestionWorkflow, MonthlyReportWorkflow],
        activities=[
            fetch_api_page,
            transform_page,
            merge_pages,
            generate_report,
            publish_report
        ]
    )

    print("[OK] Temporal worker started on queue 'etl-workers'")
    print("Listening for workflow tasks...")

    # Run worker until interrupted
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
