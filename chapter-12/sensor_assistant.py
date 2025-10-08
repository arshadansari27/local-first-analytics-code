import duckdb
import os
import sys
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import StorageContext, load_index_from_storage

# Ensure relative imports work when this file is invoked via path
sys.path.append(os.path.dirname(__file__))

from schema_context import SCHEMA  # type: ignore
from text_to_sql import nl_to_sql  # type: ignore
from semantic_search import semantic_search  # type: ignore


class SensorAssistant:
    def __init__(self):
        self.llm = Ollama(model="llama3.2:3b", request_timeout=120.0)
        self.embed_model = OllamaEmbedding(model_name="nomic-embed-text")
        self.con = duckdb.connect("sensors.db", read_only=True)

        # Load RAG index for docs (built by build_rag_index.py)
        storage_context = StorageContext.from_defaults(persist_dir="./rag_index")
        self.doc_index = load_index_from_storage(storage_context, embed_model=self.embed_model)
        self.doc_engine = self.doc_index.as_query_engine(llm=self.llm)

    def route_query(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["similar", "like", "find events"]):
            return "semantic_search"
        if any(w in q for w in ["what is", "define", "explain", "mean", "how is"]):
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
            term = question.replace("similar to", "").replace("find events like", "").strip()
            results = semantic_search(term, top_k=5)
            for *fields, score in results:
                # fields = [sensor_id, device_type, timestamp, status, temperature, pressure, searchable_text]
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
