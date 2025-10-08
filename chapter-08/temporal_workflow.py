"""
Level 4: Temporal Durable Workflows
Chapter 8: Orchestration Progression

Long-running, crash-resilient workflows with Temporal.
"""

from temporalio import workflow, activity
from datetime import timedelta
import httpx
import polars as pl
import duckdb


# Activities (units of work)
@activity.defn(name="fetch_api_page")
async def fetch_api_page(url: str, page: int) -> str:
    """Fetch one page from API."""

    # Activity-level retry (Temporal handles this)
    response = await httpx.AsyncClient().get(
        url,
        params={"page": page, "per_page": 1000}
    )
    response.raise_for_status()

    output_path = f"data/raw/page_{page:04d}.json"
    with open(output_path, 'w') as f:
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
    """Combine all pages into single Parquet."""

    conn = duckdb.connect()

    files_list = ", ".join([f"'{f}'" for f in parquet_files])

    conn.execute(f"""
        COPY (
            SELECT * FROM read_parquet([{files_list}])
        ) TO 'data/curated/full_dataset.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    return "data/curated/full_dataset.parquet"


# Workflow (orchestration)
@workflow.defn(name="paginated-ingestion")
class PaginatedIngestionWorkflow:
    """Fetch 1000 pages from API, rate-limited to 1 req/second."""

    @workflow.run
    async def run(self, base_url: str, total_pages: int) -> str:

        parquet_files = []

        # Fetch and transform each page
        for page in range(1, total_pages + 1):

            # Fetch page (with automatic retries)
            json_path = await workflow.execute_activity(
                fetch_api_page,
                args=[base_url, page],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=workflow.RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=60),
                    maximum_attempts=5
                )
            )

            # Transform to Parquet
            parquet_path = await workflow.execute_activity(
                transform_page,
                args=[json_path],
                start_to_close_timeout=timedelta(seconds=10)
            )

            parquet_files.append(parquet_path)

            # Rate limit: sleep 1 second between requests
            await workflow.sleep(1)

            # Log progress every 100 pages
            if page % 100 == 0:
                workflow.logger.info(f"Processed {page}/{total_pages} pages")

        # Merge all pages
        final_path = await workflow.execute_activity(
            merge_pages,
            args=[parquet_files],
            start_to_close_timeout=timedelta(minutes=10)
        )

        return final_path


if __name__ == "__main__":
    import asyncio
    from temporalio.client import Client

    async def main():
        client = await Client.connect("localhost:7233")

        result = await client.execute_workflow(
            PaginatedIngestionWorkflow.run,
            args=["https://api.example.com/data", 1000],
            id="paginated-ingestion-2024-10-04",
            task_queue="etl-workers"
        )

        print(f"[OK] Ingestion complete: {result}")

    asyncio.run(main())
