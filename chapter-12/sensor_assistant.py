"""Interactive CLI that routes a question to one of three tools:

- ``sql``: text → DuckDB SQL via Ollama (requires Ollama)
- ``semantic_search``: similar sensor events via sentence-transformers + DuckDB VSS
- ``docs``: RAG Q&A over the data dictionary (requires Ollama + ``rag_index``)
"""

import os
import sys

import duckdb
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

# Make sibling modules importable when invoked via path
sys.path.append(os.path.dirname(__file__))

from schema_context import SCHEMA  # type: ignore  # noqa: E402
from semantic_search import semantic_search  # type: ignore  # noqa: E402
from text_to_sql import nl_to_sql  # type: ignore  # noqa: E402

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _check_ollama_reachable() -> None:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3) as r:
            r.read()
    except (urllib.error.URLError, OSError) as e:
        raise SystemExit(
            f"Cannot reach Ollama at {OLLAMA_HOST}. Start it with:\n"
            "  ollama serve\n"
            f"then pull the model:\n  ollama pull {OLLAMA_MODEL}\n"
            f"(underlying error: {e})"
        )


class SensorAssistant:
    def __init__(self):
        _check_ollama_reachable()
        if not os.path.exists("sensors.db"):
            raise SystemExit(
                "sensors.db not found. Run:\n"
                "  python code/chapter-12/embed_sensor_logs.py"
            )
        if not os.path.isdir("rag_index"):
            raise SystemExit(
                "rag_index not found. Run:\n"
                "  python code/chapter-12/build_rag_index.py"
            )
        self.llm = Ollama(
            model=OLLAMA_MODEL, base_url=OLLAMA_HOST, request_timeout=120.0
        )
        self.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
        self.con = duckdb.connect("sensors.db", read_only=True)

        storage_context = StorageContext.from_defaults(persist_dir="./rag_index")
        self.doc_index = load_index_from_storage(
            storage_context, embed_model=self.embed_model
        )
        self.doc_engine = self.doc_index.as_query_engine(llm=self.llm)

    def route_query(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["similar", "like", "find events"]):
            return "semantic_search"
        if any(
            w in q
            for w in ["what is", "what does", "define", "explain", "mean", "how is"]
        ):
            return "docs"
        return "sql"

    def answer(self, question: str):
        tool = self.route_query(question)
        print(f"[Using: {tool}]\n")

        if tool == "sql":
            sql = nl_to_sql(question, SCHEMA)
            print(f"SQL: {sql}\n")
            print(self.con.execute(sql).fetchdf())

        elif tool == "semantic_search":
            term = (
                question.replace("similar to", "")
                .replace("find events like", "")
                .strip()
            )
            results = semantic_search(term, top_k=5, con=self.con)
            for *fields, score in results:
                # fields = [sensor_id, device_type, timestamp, status,
                #           temperature, pressure, searchable_text]
                print(f"Score: {score:.3f} | {fields[6]}")

        elif tool == "docs":
            print(self.doc_engine.query(question))


if __name__ == "__main__":
    print("Sensor Data Assistant (type 'quit' to exit)\n")
    assistant = SensorAssistant()
    while True:
        try:
            q = input("Ask: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"quit", "exit"}:
            break
        assistant.answer(q)
        print("\n" + "=" * 60 + "\n")
