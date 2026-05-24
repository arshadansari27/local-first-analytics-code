"""Natural-language → DuckDB SQL via a local Ollama model.

Requires Ollama to be running locally (``ollama serve``) with the model
specified by ``OLLAMA_MODEL`` (default ``llama3.2:3b``) pulled. The script
prints a clear, actionable error if Ollama is not reachable rather than
dumping a stack trace.
"""

import os
import sys

import duckdb
from llama_index.core import PromptTemplate
from llama_index.llms.ollama import Ollama

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

_LLM = None


def _llm() -> Ollama:
    global _LLM
    if _LLM is None:
        _LLM = Ollama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_HOST,
            request_timeout=120.0,
        )
    return _LLM


def _is_connection_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        s in msg
        for s in (
            "connection refused",
            "connection error",
            "max retries exceeded",
            "cannot connect",
            "name or service not known",
            "failed to establish",
        )
    )


def _fatal_ollama_error(exc: Exception) -> "SystemExit":
    if _is_connection_error(exc):
        return SystemExit(
            f"Cannot reach Ollama at {OLLAMA_HOST}. Start it with:\n"
            "  ollama serve\n"
            f"then pull the model:\n"
            f"  ollama pull {OLLAMA_MODEL}"
        )
    if "not found" in str(exc).lower():
        return SystemExit(
            f"Model '{OLLAMA_MODEL}' not found on the Ollama server. Pull it with:\n"
            f"  ollama pull {OLLAMA_MODEL}\n"
            f"or set OLLAMA_MODEL to a model you already have."
        )
    return SystemExit(f"Ollama call failed: {exc}")


SQL_PROMPT = PromptTemplate(
    """You are a SQL expert. Convert natural language to DuckDB SQL.

Schema:
{schema}

Rules:
- The data is stored in Parquet files, NOT a table. Always query via
  read_parquet('data/sensors/**/*.parquet') in the FROM clause.
  Do NOT write FROM sensor_readings.
- Always include LIMIT 100 unless the user specifies otherwise.
- Prefer narrowing by partition columns (year, month, day) when the question
  mentions a specific date or month.
- Return ONLY the SQL query. No prose, no markdown fences, no explanation.

Question: {question}

SQL:"""
)


def nl_to_sql(question: str, schema: str) -> str:
    prompt = SQL_PROMPT.format(schema=schema, question=question)
    try:
        response = _llm().complete(prompt)
    except Exception as e:  # noqa: BLE001 - surface a friendly message
        raise _fatal_ollama_error(e) from e
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def execute_nl_query(question: str):
    # Make sibling modules importable when run via path
    sys.path.append(os.path.dirname(__file__))
    from schema_context import SCHEMA  # type: ignore

    print(f"Question: {question}\n")
    sql = nl_to_sql(question, SCHEMA)
    print(f"Generated SQL:\n{sql}\n")
    con = duckdb.connect()
    result = con.execute(sql).fetchdf()
    print(f"Results ({len(result)} rows):")
    print(result)
    return result


if __name__ == "__main__":
    execute_nl_query(
        "Show me critical status sensors from facility B01 in December 2024"
    )
