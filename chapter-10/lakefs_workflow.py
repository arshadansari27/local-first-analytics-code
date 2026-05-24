"""
LakeFS Python Workflow
Chapter 10: Version Control for Data

Demonstrates branch -> test -> merge workflow with the high-level
``lakefs`` Python SDK (the recommended client as of lakeFS 1.x).

The legacy ``lakefs_sdk`` package still works, but the ``lakefs``
wrapper is the documented entry point and is what new code should use.
"""

import lakefs
from lakefs.client import Client
import duckdb


# Match the values used in lakefs_docker_compose.yml. In real code,
# pull these from environment variables (LAKECTL_*).
LAKEFS_HOST = "http://localhost:8000"
LAKEFS_ACCESS_KEY = "AKIAIOSFOLKFSSAMPLES"
LAKEFS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

REPO_NAME = "analytics-lake"
# lakeFS branch names DO allow slashes, but the lakeFS S3 gateway
# (which DuckDB talks to) expects ``s3://<repo>/<ref>/<path>`` where
# ``<ref>`` is the first path segment. Use a plain branch name.
EXPERIMENT_BRANCH = "experiment-new-source"


def lakefs_workflow_example():
    """Example LakeFS workflow: branch, write, commit, merge."""

    client = Client(
        host=LAKEFS_HOST,
        username=LAKEFS_ACCESS_KEY,
        password=LAKEFS_SECRET_KEY,
    )

    repo = lakefs.Repository(REPO_NAME, client=client)

    # Create experimental branch from main (idempotent: exist_ok=True).
    branch = repo.branch(EXPERIMENT_BRANCH).create(
        source_reference="main", exist_ok=True
    )

    # Write data on the branch via DuckDB through lakeFS's S3 gateway.
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_endpoint='localhost:8000';")
    con.execute(f"SET s3_access_key_id='{LAKEFS_ACCESS_KEY}';")
    con.execute(f"SET s3_secret_access_key='{LAKEFS_SECRET_KEY}';")
    con.execute("SET s3_url_style='path';")
    con.execute("SET s3_use_ssl=false;")
    con.execute(
        f"""
        COPY (SELECT * FROM read_parquet('local_file.parquet'))
        TO 's3://{REPO_NAME}/{EXPERIMENT_BRANCH}/data/staging/sales.parquet'
        (FORMAT 'parquet');
        """
    )

    # Commit changes on the branch.
    branch.commit(
        message="Add new sales source",
        metadata={"pipeline": "ingest_v2"},
    )

    # Validate results, run tests...
    # If good, merge into main.
    branch.merge_into("main", message=f"Merge {EXPERIMENT_BRANCH} into main")

    print("[OK] Branch merged to main")


def lakefs_with_git_metadata():
    """Link a lakeFS commit to the current Git commit for an audit trail."""
    import subprocess

    git_sha = (
        subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    )

    client = Client(
        host=LAKEFS_HOST,
        username=LAKEFS_ACCESS_KEY,
        password=LAKEFS_SECRET_KEY,
    )

    repo = lakefs.Repository(REPO_NAME, client=client)
    main = repo.branch("main")

    main.commit(
        message=f"Pipeline run {git_sha[:7]}",
        metadata={
            "git_commit": git_sha,
            "pipeline_version": "v2.1.0",
        },
    )

    print(f"[OK] LakeFS commit linked to Git {git_sha[:7]}")


if __name__ == "__main__":
    lakefs_workflow_example()
    lakefs_with_git_metadata()
