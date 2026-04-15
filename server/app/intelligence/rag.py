"""
Q&Ace — Sentence-BERT + ChromaDB RAG Retrieval.

Embeds the latest transcript and retrieves the top-k most
relevant rubric passages from ChromaDB. Target: <15 ms.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("qace.rag")

# Module-level singleton — loaded once.
_chroma_client: Any = None
_collection: Any = None


@dataclass
class RAGResult:
    """Passages retrieved from ChromaDB for prompt enrichment."""
    passages: list[str] = field(default_factory=list)
    metadatas: list[dict] = field(default_factory=list)
    distances: list[float] = field(default_factory=list)
    retrieval_ms: float = 0.0


def _resolve_embed_device(device_pref: str) -> str:
    """Resolve embedding device with CPU-safe defaults on Windows."""
    pref = (device_pref or "cpu").strip().lower()
    if pref in {"cpu", "cuda", "mps"}:
        return pref
    if pref == "auto":
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"
    return "cpu"


def init_rag(chroma_dir: str, embed_device: str = "cpu") -> bool:
    """
    Initialise the ChromaDB persistent client and open the rubrics collection.
    Call once at server startup.  Returns True on success.
    """
    global _chroma_client, _collection
    chroma_path = Path(chroma_dir)
    if not chroma_path.exists():
        logger.warning("ChromaDB directory not found at %s — RAG disabled", chroma_path)
        return False

    try:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        resolved_device = _resolve_embed_device(embed_device)
        try:
            embed_fn = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2",
                device=resolved_device,
            )
        except TypeError:
            # Some chromadb builds expose `model_kwargs` instead of `device`.
            try:
                embed_fn = SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2",
                    model_kwargs={"device": resolved_device},
                )
            except TypeError:
                logger.warning(
                    "RAG embedding function does not accept device/model_kwargs; using library defaults"
                )
                embed_fn = SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2",
                )
        _chroma_client = chromadb.PersistentClient(path=str(chroma_path))
        _collection = _chroma_client.get_collection(
            name="rubrics",
            embedding_function=embed_fn,
        )
        count = _collection.count()
        logger.info("RAG initialised ✓ (%d rubric chunks in ChromaDB, device=%s)", count, resolved_device)
        return True
    except ImportError:
        logger.warning("chromadb / sentence-transformers not installed — RAG disabled")
    except Exception as exc:
        logger.warning("RAG init failed: %s", exc)
    return False


def retrieve(transcript: str, category: Optional[str] = None, top_k: int = 3) -> RAGResult:
    """
    Retrieve top-k rubric passages relevant to *transcript*.

    Args:
        transcript: The candidate's response text.
        category: Optional filter (e.g. "behavioral", "technical", "leadership").
        top_k: Number of passages to retrieve.

    Returns:
        RAGResult with passages, metadata, distances, and timing.
    """
    if _collection is None or not transcript.strip():
        return RAGResult()

    t0 = time.perf_counter()
    try:
        where_filter = {"category": category} if category else None
        results = _collection.query(
            query_texts=[transcript],
            n_results=top_k,
            where=where_filter,
        )

        passages = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []
        ms = (time.perf_counter() - t0) * 1000.0

        logger.info(
            "RAG retrieved %d passages in %.1fms (category=%s)",
            len(passages), ms, category,
        )
        return RAGResult(
            passages=passages,
            metadatas=metadatas,
            distances=distances,
            retrieval_ms=round(ms, 1),
        )
    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        ms = (time.perf_counter() - t0) * 1000.0
        return RAGResult(retrieval_ms=round(ms, 1))
