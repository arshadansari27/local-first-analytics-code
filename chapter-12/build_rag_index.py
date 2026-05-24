"""Build a local RAG index over the Markdown data dictionary.

Embeddings use sentence-transformers (no server required); generation uses
Ollama. The script fails fast with a clear message if Ollama isn't running.
Sample dictionary files are created automatically when ``data/data_dictionary``
is missing so the script is runnable end-to-end without manual setup.
"""

import os
import sys

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

DOCS_DIR = "data/data_dictionary"

SAMPLE_FIELD_DEFINITIONS = """# Field Definitions

- `timestamp`: Reading time (TIMESTAMP, UTC)
- `sensor_id`: Unique sensor identifier (VARCHAR)
- `device_type`: One of `pump`, `motor`, `compressor`
- `temperature`: Sensor temperature in Celsius (DOUBLE)
- `pressure`: Sensor pressure in PSI (DOUBLE)
- `vibration`: Mechanical vibration in mm/s (DOUBLE)
- `status`: One of `normal`, `warning`, `critical`
- `facility`: Building/facility code (VARCHAR)
"""

SAMPLE_BUSINESS_RULES = """# Business Rules

- `status = warning` is set when any reading approaches a critical threshold:
  temperature 85-92°C, pressure 145-152 PSI, or vibration 10-12 mm/s.
- `status = critical` indicates a reading exceeded a critical threshold
  (temperature > 92°C, pressure > 152 PSI, or vibration > 12 mm/s) and
  requires immediate maintenance attention.
- Normal vibration range for healthy rotating equipment is 0-8 mm/s.
  Values above 10 mm/s suggest bearing wear or misalignment.
- Pumps in facility B03 historically run 2-3°C hotter than other facilities;
  adjust comparisons accordingly.
"""


def _ensure_sample_docs() -> None:
    if os.path.isdir(DOCS_DIR) and any(
        f.endswith(".md") for f in os.listdir(DOCS_DIR)
    ):
        return
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "field_definitions.md"), "w") as f:
        f.write(SAMPLE_FIELD_DEFINITIONS)
    with open(os.path.join(DOCS_DIR, "business_rules.md"), "w") as f:
        f.write(SAMPLE_BUSINESS_RULES)
    print(f"Wrote sample documentation to {DOCS_DIR}/")


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


def main() -> None:
    _ensure_sample_docs()
    _check_ollama_reachable()

    print(f"Loading Markdown files from {DOCS_DIR}...")
    docs = SimpleDirectoryReader(input_dir=DOCS_DIR, recursive=False).load_data()
    if not docs:
        raise SystemExit(f"No documents found in {DOCS_DIR}.")

    # LLM is configured so downstream queries can use it; the index build
    # itself only requires the embed_model.
    llm = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, request_timeout=120.0)
    print(f"Loading embedding model '{EMBED_MODEL}'...")
    embed = HuggingFaceEmbedding(model_name=EMBED_MODEL)

    print("Building vector index...")
    index = VectorStoreIndex.from_documents(docs, embed_model=embed)
    index.storage_context.persist(persist_dir="rag_index")
    print("Index persisted to ./rag_index")
    # Quick smoke check that the LLM works (one-token completion)
    try:
        llm.complete("ok")
    except Exception as e:  # noqa: BLE001
        print(
            f"Warning: Ollama LLM smoke check failed ({e}). The index was built "
            f"but queries against {OLLAMA_MODEL} may fail.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
