"""Document chunker and indexer for operational knowledge bases.

Processes runbooks, architectural docs, and post-mortems into searchable
chunks suitable for vector or lexical indexing.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from opsbrain.rag.store import Document


class DocumentChunk(BaseModel):
    """A segment of an indexed document."""

    chunk_id: str
    doc_title: str
    content: str
    section_title: str = ""
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentIndexer:
    """Chunks text and Markdown documents into indexed chunks."""

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(
        self,
        text: str,
        *,
        doc_id: str,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Split plain text into overlapping chunks."""
        meta = metadata or {}
        chunks: list[Document] = []
        start = 0
        text_len = len(text)
        idx = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk_content = text[start:end].strip()

            if chunk_content:
                chunk_meta = dict(meta)
                chunk_meta.update({
                    "title": title or doc_id,
                    "chunk_index": idx,
                    "source": doc_id,
                })
                chunks.append(
                    Document(
                        doc_id=f"{doc_id}_chunk_{idx}",
                        content=chunk_content,
                        metadata=chunk_meta,
                        tags=meta.get("tags", []),
                    )
                )
                idx += 1

            if end >= text_len:
                break
            start += max(1, self.chunk_size - self.chunk_overlap)

        return chunks

    def chunk_markdown_by_headings(
        self,
        markdown_text: str,
        *,
        doc_id: str,
        title: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Split Markdown document logically by level 1-3 headings."""
        meta = metadata or {}
        sections = re.split(r"(^#{1,3}\s+.+$)", markdown_text, flags=re.MULTILINE)

        chunks: list[Document] = []
        current_heading = title or "Introduction"
        current_content: list[str] = []
        idx = 0

        for part in sections:
            part = part.strip()
            if not part:
                continue

            if part.startswith("#"):
                # Save previous section if present
                if current_content:
                    full_text = "\n\n".join(current_content).strip()
                    if full_text:
                        chunk_meta = dict(meta)
                        chunk_meta.update({
                            "title": title or doc_id,
                            "heading": current_heading,
                            "chunk_index": idx,
                        })
                        chunks.append(
                            Document(
                                doc_id=f"{doc_id}_sec_{idx}",
                                content=f"## {current_heading}\n\n{full_text}",
                                metadata=chunk_meta,
                                tags=meta.get("tags", []),
                            )
                        )
                        idx += 1
                    current_content = []
                current_heading = part.lstrip("#").strip()
            else:
                current_content.append(part)

        # Append final section
        if current_content:
            full_text = "\n\n".join(current_content).strip()
            if full_text:
                chunk_meta = dict(meta)
                chunk_meta.update({
                    "title": title or doc_id,
                    "heading": current_heading,
                    "chunk_index": idx,
                })
                chunks.append(
                    Document(
                        doc_id=f"{doc_id}_sec_{idx}",
                        content=f"## {current_heading}\n\n{full_text}",
                        metadata=chunk_meta,
                        tags=meta.get("tags", []),
                    )
                )

        # Fallback to plain chunking if no markdown headings were detected
        if not chunks:
            return self.chunk_text(markdown_text, doc_id=doc_id, title=title, metadata=metadata)

        return chunks
