import chromadb
from chromadb.utils import embedding_functions
from app.core.logger import get_logger

logger = get_logger("rag")

# ChromaDB persistent client — stores vectors on disk
client = chromadb.PersistentClient(path="chroma_db")

# Use sentence-transformers for embeddings (free, runs locally)
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def get_or_create_collection(collection_name: str = "slatefall_dossier"):
    """Get existing collection or create a new one."""
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks.
    Smaller chunks (500 chars) work better for semantic search
    than the 1500 we used before.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def index_sections(sections: dict) -> None:
    """
    Index all sections into ChromaDB.
    Each chunk gets a unique ID and metadata about which section it came from.
    Only indexes if not already done.
    """
    collection = get_or_create_collection()

    # Check if already indexed
    existing = collection.count()
    if existing > 0:
        logger.info(f"ChromaDB already has {existing} chunks indexed — skipping reindex")
        return

    logger.info("Indexing SLATEFALL dossier into ChromaDB...")

    all_chunks = []
    all_ids = []
    all_metadata = []

    for section_id, data in sections.items():
        chunks = chunk_text(data["content"])
        logger.info(f"Section {section_id}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            chunk_id = f"section_{section_id}_chunk_{i}"
            all_chunks.append(chunk)
            all_ids.append(chunk_id)
            all_metadata.append({
                "section_id": section_id,
                "section_title": data["title"],
                "chunk_index": i
            })

    # Add to ChromaDB in batches
    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        collection.add(
            documents=all_chunks[i:i+batch_size],
            ids=all_ids[i:i+batch_size],
            metadatas=all_metadata[i:i+batch_size]
        )
        logger.info(f"Indexed batch {i//batch_size + 1}")

    logger.info(f"Indexing complete — {len(all_chunks)} chunks stored in ChromaDB")


def retrieve_relevant_chunks(
    query: str,
    section_ids: list[int],
    n_results: int = 5
) -> str:
    """
    Retrieve the most semantically relevant chunks for a query,
    filtered to specific sections.

    This replaces our simple keyword-based chunking with proper
    vector similarity search.
    """
    collection = get_or_create_collection()

    # Filter to only the requested sections
    where_filter = {
        "section_id": {"$in": section_ids}
    }

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter
    )

    # Combine retrieved chunks into context string
    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]

    context = ""
    for chunk, meta in zip(chunks, metadatas):
        context += f"[Section {meta['section_id']}: {meta['section_title']}]\n"
        context += chunk + "\n\n"

    logger.debug(f"Retrieved {len(chunks)} chunks for query: {query[:50]}...")
    return context.strip()


if __name__ == "__main__":
    # Test the RAG system
    from app.core.pdf_parser import extract_sections

    sections = extract_sections("SLATEFALL_DOSSIER.pdf")
    index_sections(sections)

    # Test retrieval
    result = retrieve_relevant_chunks(
        query="What are the power limits of inertial suspension?",
        section_ids=[2],
        n_results=3
    )
    print("\nRetrieved context:")
    print(result)