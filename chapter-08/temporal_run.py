#!/usr/bin/env python3
"""
Execute Temporal Workflows

Run workflows from command line.
"""

import asyncio
from temporalio.client import Client
from temporal_workflow import PaginatedIngestionWorkflow, MonthlyReportWorkflow


async def run_paginated_ingestion():
    """Execute paginated ingestion workflow."""
    client = await Client.connect("localhost:7233")

    print("Starting paginated ingestion workflow...")

    result = await client.execute_workflow(
        PaginatedIngestionWorkflow.run,
        args=["https://api.example.com/data", 100],  # 100 pages
        id="paginated-ingestion-2024-10-07",
        task_queue="etl-workers"
    )

    print(f"[OK] Ingestion complete: {result}")


async def run_monthly_report():
    """Execute monthly report workflow with approval."""
    client = await Client.connect("localhost:7233")

    print("Starting monthly report workflow...")

    # Start workflow (will wait for approval signal)
    handle = await client.start_workflow(
        MonthlyReportWorkflow.run,
        args=["2024-10"],
        id="monthly-report-2024-10",
        task_queue="etl-workers"
    )

    print(f"[OK] Workflow started: {handle.id}")
    print("To approve, run:")
    print(f"  temporal workflow signal --workflow-id {handle.id} --name approve")

    # Optionally wait for result
    # result = await handle.result()
    # print(f"[OK] Report workflow complete: {result}")


async def send_approval_signal(workflow_id: str):
    """Send approval signal to workflow."""
    client = await Client.connect("localhost:7233")

    handle = client.get_workflow_handle(workflow_id)
    await handle.signal("approve")

    print(f"[OK] Approval signal sent to {workflow_id}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python temporal_run.py ingestion  # Run paginated ingestion")
        print("  python temporal_run.py report     # Run monthly report")
        print("  python temporal_run.py approve <workflow-id>  # Send approval")
        sys.exit(1)

    command = sys.argv[1]

    if command == "ingestion":
        asyncio.run(run_paginated_ingestion())
    elif command == "report":
        asyncio.run(run_monthly_report())
    elif command == "approve" and len(sys.argv) > 2:
        asyncio.run(send_approval_signal(sys.argv[2]))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
