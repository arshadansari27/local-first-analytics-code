"""
LakeFS Python Workflow
Chapter 10: Version Control for Data

Demonstrates branch -> test -> merge workflow with LakeFS.
"""

import lakefs_sdk
from lakefs_sdk.client import LakeFSClient
import duckdb


def lakefs_workflow_example():
    """Example LakeFS workflow: Branch, commit, merge."""
    
    # Configure client
    config = lakefs_sdk.Configuration(
        host="http://localhost:8000",
        username="admin",
        password="admin"
    )
    client = LakeFSClient(config)

    # Create experimental branch
    branch = client.branches.create_branch(
        repository="analytics-lake",
        branch_creation={
            "name": "experiment/new-source",
            "source": "main"
        }
    )

    # Write data to the branch (not main!)
    # Use S3-compatible path: s3://analytics-lake/experiment/new-source/data/...
    con = duckdb.connect()
    con.execute("""
        COPY (SELECT * FROM read_parquet('local_file.parquet'))
        TO 's3://analytics-lake/experiment/new-source/data/staging/sales.parquet'
        (FORMAT 'parquet');
    """)

    # Commit changes on branch
    client.commits.commit(
        repository="analytics-lake",
        branch="experiment/new-source",
        commit_creation={
            "message": "Add new sales source",
            "metadata": {"pipeline": "ingest_v2"}
        }
    )

    # Validate results, run tests...
    # If good, merge to main
    client.refs.merge_into_branch(
        repository="analytics-lake",
        source_ref="experiment/new-source",
        destination_branch="main"
    )

    print("[OK] Branch merged to main")


def lakefs_with_git_metadata():
    """Link LakeFS commits to Git commits for full audit trail."""
    import subprocess
    
    # Get current Git commit
    git_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()

    config = lakefs_sdk.Configuration(
        host="http://localhost:8000",
        username="admin",
        password="admin"
    )
    client = LakeFSClient(config)

    # Commit to LakeFS with Git metadata
    client.commits.commit(
        repository="analytics-lake",
        branch="main",
        commit_creation={
            "message": f"Pipeline run {git_sha[:7]}",
            "metadata": {
                "git_commit": git_sha,
                "pipeline_version": "v2.1.0",
                "timestamp": "2024-10-05T10:30:00Z"
            }
        }
    )

    print(f"[OK] LakeFS commit linked to Git {git_sha[:7]}")


if __name__ == "__main__":
    lakefs_workflow_example()
    lakefs_with_git_metadata()
