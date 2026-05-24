"""
Level 4: Temporal Durable Workflows
Chapter 8: Orchestration Progression

Long-running, crash-resilient workflows with Temporal.

NOTE on imports: Temporal's workflow sandbox re-imports this module under a
restricted runtime, so non-deterministic libraries (httpx, polars, duckdb)
must be imported inside ``workflow.unsafe.imports_passed_through()``. The
activities themselves run outside the sandbox and may use any library.
"""

from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Sandbox-safe imports: activities run outside the sandbox, but the module is
# imported by the worker to register both workflows and activities.
with workflow.unsafe.imports_passed_through():
    import duckdb
    import httpx
    import polars as pl


# ---------------------------------------------------------------------------
# Activities (units of work) — run in normal Python, outside the sandbox.
# ---------------------------------------------------------------------------
@activity.defn(name="fetch_api_page")
async def fetch_api_page(url: str, page: int) -> str:
    """Fetch one page from API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={"page": page, "per_page": 1000},
            timeout=30.0,
        )
        response.raise_for_status()

    output_path = f"data/raw/page_{page:04d}.json"
    with open(output_path, "w") as f:
        f.write(response.text)

    return output_path


@activity.defn(name="transform_page")
def transform_page(json_path: str) -> str:
    """Convert JSON page to Parquet."""
    df = pl.read_json(json_path)
    df = df.filter(pl.col("id").is_not_null())

    parquet_path = json_path.replace(".json", ".parquet")
    df.write_parquet(parquet_path)

    return parquet_path


@activity.defn(name="merge_pages")
def merge_pages(parquet_files: list[str]) -> str:
    """Combine all pages into a single Parquet."""
    conn = duckdb.connect()
    files_list = ", ".join(f"'{f}'" for f in parquet_files)

    conn.execute(
        f"""
        COPY (
            SELECT * FROM read_parquet([{files_list}])
        ) TO 'data/curated/full_dataset.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )

    return "data/curated/full_dataset.parquet"


@activity.defn(name="generate_report")
def generate_report(month: str) -> str:
    """Generate a monthly report. Stub: writes a placeholder file."""
    output_path = f"data/curated/report_{month}.parquet"
    # Real implementation would build the report from upstream tables.
    pl.DataFrame({"month": [month], "status": ["draft"]}).write_parquet(output_path)
    return output_path


@activity.defn(name="publish_report")
def publish_report(report_path: str) -> str:
    """Publish a report. Stub: returns the published path."""
    # Real implementation would upload to S3, email stakeholders, etc.
    return report_path


# ---------------------------------------------------------------------------
# Workflows (orchestration) — run inside Temporal's deterministic sandbox.
# ---------------------------------------------------------------------------
@workflow.defn(name="paginated-ingestion")
class PaginatedIngestionWorkflow:
    """Fetch ``total_pages`` pages from an API, rate-limited to 1 req/second."""

    @workflow.run
    async def run(self, base_url: str, total_pages: int) -> str:
        parquet_files: list[str] = []

        for page in range(1, total_pages + 1):
            # Fetch page (with automatic retries handled by Temporal)
            json_path = await workflow.execute_activity(
                fetch_api_page,
                args=[base_url, page],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=60),
                    maximum_attempts=5,
                ),
            )

            # Transform to Parquet
            parquet_path = await workflow.execute_activity(
                transform_page,
                args=[json_path],
                start_to_close_timeout=timedelta(seconds=10),
            )

            parquet_files.append(parquet_path)

            # Rate limit: durable sleep between requests
            await workflow.sleep(1)

            if page % 100 == 0:
                workflow.logger.info(f"Processed {page}/{total_pages} pages")

        # Merge all pages
        final_path = await workflow.execute_activity(
            merge_pages,
            args=[parquet_files],
            start_to_close_timeout=timedelta(minutes=10),
        )

        return final_path


@workflow.defn(name="monthly-report-with-approval")
class MonthlyReportWorkflow:
    """Generate a monthly report, then wait for human approval before publishing."""

    def __init__(self) -> None:
        self.approved: bool = False

    @workflow.signal
    def approve(self) -> None:
        """Called externally to approve the report."""
        self.approved = True

    @workflow.run
    async def run(self, month: str) -> str:
        # Step 1: Generate the report
        report_path = await workflow.execute_activity(
            generate_report,
            args=[month],
            start_to_close_timeout=timedelta(hours=1),
        )

        # Step 2: Wait up to 7 days for an approval signal.
        try:
            await workflow.wait_condition(
                lambda: self.approved,
                timeout=timedelta(days=7),
            )
        except TimeoutError:
            return "Report expired without approval"

        # Step 3: Publish the report
        await workflow.execute_activity(
            publish_report,
            args=[report_path],
            start_to_close_timeout=timedelta(minutes=5),
        )

        return f"Report published: {report_path}"


if __name__ == "__main__":
    import asyncio

    from temporalio.client import Client

    async def main() -> None:
        client = await Client.connect("localhost:7233")

        result = await client.execute_workflow(
            PaginatedIngestionWorkflow.run,
            args=["https://api.example.com/data", 1000],
            id="paginated-ingestion-2024-10-04",
            task_queue="etl-workers",
        )

        print(f"[OK] Ingestion complete: {result}")

    asyncio.run(main())
