"""Document and Vector store for runbooks, postmortems, and architectural docs.

Provides in-memory vector similarity and keyword search with metadata
filtering, with support for persistence.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class Document(BaseModel):
    """A document or chunk stored in the operational knowledge base."""

    doc_id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    tags: list[str] = Field(default_factory=list)


class DocumentStore(ABC):
    """Abstract interface for storing and retrieving operational documents."""

    @abstractmethod
    def add(self, document: Document) -> None:
        """Add a single document to the store."""

    @abstractmethod
    def add_many(self, documents: list[Document]) -> None:
        """Add multiple documents in bulk."""

    @abstractmethod
    def get(self, doc_id: str) -> Document | None:
        """Fetch a document by its unique ID."""

    @abstractmethod
    def count(self) -> int:
        """Return total stored documents."""


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class VectorStore(DocumentStore):
    """In-memory document and vector store with similarity scoring."""

    def __init__(self) -> None:
        self._docs: dict[str, Document] = {}

    def add(self, document: Document) -> None:
        self._docs[document.doc_id] = document

    def add_many(self, documents: list[Document]) -> None:
        for doc in documents:
            self.add(doc)

    def get(self, doc_id: str) -> Document | None:
        return self._docs.get(doc_id)

    def count(self) -> int:
        return len(self._docs)

    def search_vector(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """Find closest documents using cosine similarity of embeddings."""
        candidates = list(self._docs.values())
        if metadata_filter:
            candidates = [
                d for d in candidates
                if all(d.metadata.get(k) == v for k, v in metadata_filter.items())
            ]

        scored: list[tuple[Document, float]] = []
        for doc in candidates:
            if doc.embedding:
                score = _cosine_similarity(query_embedding, doc.embedding)
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def search_keyword(
        self,
        query: str,
        *,
        limit: int = 5,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        """Lexical search based on token overlap."""
        terms = set(query.lower().split())
        candidates = list(self._docs.values())
        if metadata_filter:
            candidates = [
                d for d in candidates
                if all(d.metadata.get(k) == v for k, v in metadata_filter.items())
            ]

        scored: list[tuple[Document, float]] = []
        for doc in candidates:
            content_lower = doc.content.lower()
            overlap = sum(1 for t in terms if t in content_lower)
            if overlap > 0:
                score = overlap / max(len(terms), 1)
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]
