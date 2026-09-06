"""Unit tests for the RAG pipeline — store, indexer, retriever."""

from __future__ import annotations

import pytest

from opsbrain.rag.indexer import DocumentIndexer
from opsbrain.rag.retriever import RAGRetriever
from opsbrain.rag.store import Document, VectorStore


class TestVectorStore:
    def test_store_add_and_count(self):
        store = VectorStore()
        assert store.count() == 0

        doc1 = Document(doc_id="doc1", content="Payment service architecture", metadata={"tier": "backend"})
        doc2 = Document(doc_id="doc2", content="Database connection pooling", metadata={"tier": "data"})
        store.add_many([doc1, doc2])

        assert store.count() == 2
        assert store.get("doc1") == doc1

    def test_keyword_search(self):
        store = VectorStore()
        store.add(Document(doc_id="doc1", content="Postgres connection pool exhaustion runbook"))
        store.add(Document(doc_id="doc2", content="Kubernetes pod deployment guide"))

        results = store.search_keyword("connection pool")
        assert len(results) >= 1
        assert results[0][0].doc_id == "doc1"
        assert results[0][1] > 0.0

    def test_vector_search(self):
        store = VectorStore()
        store.add(Document(doc_id="d1", content="Text 1", embedding=[1.0, 0.0, 0.0]))
        store.add(Document(doc_id="d2", content="Text 2", embedding=[0.0, 1.0, 0.0]))

        # Search with vector close to d1
        results = store.search_vector([0.9, 0.1, 0.0])
        assert len(results) == 2
        assert results[0][0].doc_id == "d1"
        assert results[0][1] > 0.8

    def test_metadata_filtering(self):
        store = VectorStore()
        store.add(Document(doc_id="d1", content="Memory leak", metadata={"service": "payment"}))
        store.add(Document(doc_id="d2", content="Memory leak", metadata={"service": "auth"}))

        results = store.search_keyword("memory", metadata_filter={"service": "payment"})
        assert len(results) == 1
        assert results[0][0].doc_id == "d1"


class TestDocumentIndexer:
    def test_plain_text_chunking(self):
        indexer = DocumentIndexer(chunk_size=50, chunk_overlap=10)
        long_text = "This is a sentence explaining how to troubleshoot database pool exhaustion issues when latency spikes occur."
        chunks = indexer.chunk_text(long_text, doc_id="troubleshoot_doc")

        assert len(chunks) > 1
        assert all(c.doc_id.startswith("troubleshoot_doc") for c in chunks)

    def test_markdown_heading_chunking(self):
        indexer = DocumentIndexer()
        md = """
# Runbook: DB Pool

First paragraph about overview.

## Section 1: Symptoms

Connection timeouts and 504 errors.

## Section 2: Remediation

Restart service and bump pool size.
"""
        chunks = indexer.chunk_markdown_by_headings(md, doc_id="rb_db")
        assert len(chunks) >= 2
        headings = [c.metadata.get("heading") for c in chunks]
        assert any("Symptoms" in str(h) for h in headings)


class TestRAGRetriever:
    def test_retriever_query_and_formatting(self):
        store = VectorStore()
        store.add(Document(
            doc_id="rb_pg",
            content="To fix connection pool exhaustion: scale pool size in config and restart pods.",
            metadata={"title": "PostgreSQL Recovery Runbook"},
        ))

        retriever = RAGRetriever(store)
        result = retriever.retrieve("connection pool")

        assert len(result.documents) == 1
        context_str = result.to_context_string()
        assert "PostgreSQL Recovery Runbook" in context_str
        assert "scale pool size" in context_str
