import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding


def main():
    docs_dir = "data/data_dictionary"
    if not os.path.isdir(docs_dir):
        raise SystemExit(
            f"Directory '{docs_dir}' not found. Create it and add Markdown files (e.g., field_definitions.md)."
        )

    print(f"Loading Markdown files from {docs_dir}...")
    docs = SimpleDirectoryReader(input_dir=docs_dir, recursive=False).load_data()
    if not docs:
        raise SystemExit("No documents found. Place .md files in data/data_dictionary.")

    llm = Ollama(model="llama3.2:3b", request_timeout=120.0)
    embed = OllamaEmbedding(model_name="nomic-embed-text")

    print("Building vector index...")
    index = VectorStoreIndex.from_documents(docs, embed_model=embed)
    storage = StorageContext.from_defaults(persist_dir="rag_index")
    index.storage_context.persist(persist_dir="rag_index")
    print("Index persisted to ./rag_index")


if __name__ == "__main__":
    main()

