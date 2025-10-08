import duckdb
import pandas as pd
from tqdm import tqdm
from llama_index.embeddings.ollama import OllamaEmbedding


def create_searchable_text(row: pd.Series) -> str:
    return (
        f"{row['device_type']} sensor {row['sensor_id']} at {row['facility']}: "
        f"status {row['status']}, temp {row['temperature']}°C, "
        f"pressure {row['pressure']} PSI, vibration {row['vibration']} mm/s"
    )


def main():
    embed_model = OllamaEmbedding(model_name="nomic-embed-text", base_url="http://localhost:11434")

    con = duckdb.connect("sensors.db")
    # Sample interesting rows for embedding
    df = con.execute(
        """
        SELECT *
        FROM read_parquet('data/sensors/**/*.parquet')
        WHERE status != 'normal'
        USING SAMPLE 100000 ROWS -- at most 100k rows
        """
    ).fetchdf()

    if df.empty:
        print("No data found under data/sensors/. Generate dataset first.")
        return

    texts = [create_searchable_text(row) for _, row in df.iterrows()]

    print(f"Generating embeddings for {len(texts)} rows...")
    embeddings = []
    for t in tqdm(texts, unit="row"):
        embeddings.append(embed_model.get_text_embedding(t))

    df["searchable_text"] = texts
    df["embedding"] = embeddings

    con.execute("DROP TABLE IF EXISTS sensor_embeddings")
    con.register("tmp_df", df)
    con.execute(
        """
        CREATE TABLE sensor_embeddings AS
        SELECT * FROM tmp_df
        """
    )
    con.unregister("tmp_df")
    print("Created table sensor_embeddings in sensors.db")


if __name__ == "__main__":
    main()

