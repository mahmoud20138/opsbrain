"""RAG Retriever — retrieves relevant operational context for agents.

Queries the VectorStore / DocumentStore to inject runbooks, architecture specs,
and post-mortems into agent prompts.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from opsbrain.rag.store import Document, VectorStore


class RetrievalResult(BaseModel):
    """Result of a RAG retrieval query."""

    query: str
    documents: list[Document] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)

    def to_context_string(self) -> str:
        """Format retrieved documents as a Markdown block for agent prompts."""
        if not self.documents:
            return ""

        parts = ["### Relevant Operational Runbooks & Documentation:\n"]
        for i, (doc, score) in enumerate(zip(self.documents, self.scores, strict=False), 1):
            title = doc.metadata.get("title", doc.doc_id)
            parts.append(f"**[{i}] {title}** (relevance: {score:.2f}):\n{doc.content}\n")
        return "\n".join(parts)


class RAGRetriever:
    """Retrieves operational knowledge for agent consumption.

    Usage::

        retriever = RAGRetriever(vector_store)
        res = retriever.retrieve("Payment service connection pool exhausted")
        prompt_context = res.to_context_string()
    """

    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 3,
        metadata_filter: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> RetrievalResult:
        """Retrieve the top matching documents for an operational query."""
        if query_embedding:
            results = self.store.search_vector(
                query_embedding,
                limit=limit,
                metadata_filter=metadata_filter,
            )
        else:
            results = self.store.search_keyword(
                query,
                limit=limit,
                metadata_filter=metadata_filter,
            )

        docs = [item[0] for item in results]
        scores = [item[1] for item in results]

        return RetrievalResult(query=query, documents=docs, scores=scores)
