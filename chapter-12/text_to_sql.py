import duckdb
import os
import sys
from llama_index.llms.ollama import Ollama
from llama_index.core import PromptTemplate


_LLM = None


def _llm():
    global _LLM
    if _LLM is None:
        _LLM = Ollama(model="llama3.2:3b", request_timeout=120.0)
    return _LLM


SQL_PROMPT = PromptTemplate(
    """You are a SQL expert. Convert natural language to DuckDB SQL.

Schema:
{schema}

Rules:
- Use Parquet file paths: read_parquet('data/sensors/**/*.parquet')
- Always include LIMIT unless user specifies otherwise
- Use date partitions for performance when possible (year/month/day)
- Return ONLY the SQL query, no explanation

Question: {question}

SQL:"""
)


def nl_to_sql(question: str, schema: str) -> str:
    prompt = SQL_PROMPT.format(schema=schema, question=question)
    response = _llm().complete(prompt)
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    return sql


def execute_nl_query(question: str):
    # Ensure local imports work when run via path
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
