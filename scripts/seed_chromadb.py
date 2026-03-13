"""
Q&Ace — ChromaDB Seeding Script.

Reads STAR rubric markdown files from data/rubrics/,
chunks them by section (## headings), embeds with Sentence-BERT,
and stores in a persistent ChromaDB collection.

Usage:
    python scripts/seed_chromadb.py

Creates/overwrites: data/chroma/ (persistent ChromaDB directory).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Add project root to path so we can import app modules
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

RUBRICS_DIR = REPO_ROOT / "data" / "rubrics"
CHROMA_DIR = REPO_ROOT / "data" / "chroma"


def chunk_markdown(text: str, source: str) -> list[dict]:
    """Split markdown by ## headings into chunks with metadata."""
    chunks: list[dict] = []
    # Split on ## headings
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        # Extract heading
        heading_match = re.match(r"^##\s+(.+)", section)
        heading = heading_match.group(1).strip() if heading_match else "Introduction"
        chunks.append({
            "text": section,
            "source": source,
            "heading": heading,
        })
    # If no ## headings found, return the whole file as one chunk
    if not chunks:
        chunks.append({
            "text": text.strip(),
            "source": source,
            "heading": "Full Document",
        })
    return chunks


def seed():
    """Read rubrics, chunk, embed, and store in ChromaDB."""
    try:
        import chromadb
    except ImportError:
        print("ERROR: chromadb not installed. Run: pip install chromadb")
        sys.exit(1)

    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError:
        print("ERROR: sentence-transformers not installed. Run: pip install sentence-transformers")
        sys.exit(1)

    # Collect all rubric files
    rubric_files = sorted(RUBRICS_DIR.glob("*.md"))
    if not rubric_files:
        print(f"No rubric .md files found in {RUBRICS_DIR}")
        sys.exit(1)

    print(f"Found {len(rubric_files)} rubric file(s): {[f.name for f in rubric_files]}")

    # Chunk all rubrics
    all_chunks: list[dict] = []
    for rubric_file in rubric_files:
        text = rubric_file.read_text(encoding="utf-8")
        category = rubric_file.stem  # e.g., "behavioral", "technical"
        chunks = chunk_markdown(text, category)
        for chunk in chunks:
            chunk["category"] = category
        all_chunks.extend(chunks)
        print(f"  {rubric_file.name}: {len(chunks)} chunks")

    print(f"Total chunks: {len(all_chunks)}")

    # Set up ChromaDB with Sentence-BERT embeddings
    embed_fn = SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2",
    )

    # Create/reset persistent client
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete existing collection if present
    try:
        client.delete_collection("rubrics")
        print("Deleted existing 'rubrics' collection")
    except Exception:
        pass

    collection = client.create_collection(
        name="rubrics",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Add chunks
    ids = []
    documents = []
    metadatas = []
    for i, chunk in enumerate(all_chunks):
        chunk_id = f"{chunk['category']}_{i:03d}"
        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "source": chunk["source"],
            "heading": chunk["heading"],
            "category": chunk["category"],
        })

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Seeded {collection.count()} chunks into ChromaDB at {CHROMA_DIR}")
    print("Done ✓")


if __name__ == "__main__":
    seed()
