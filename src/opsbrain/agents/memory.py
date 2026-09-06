"""Agent memory system — short-term and long-term memory for agents.

Short-term memory is the conversation history within a session.
Long-term memory stores past incidents, solutions, and learnings for
retrieval-augmented reasoning.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class MemoryEntry(BaseModel):
    """A single entry in long-term memory."""

    id: str = ""
    category: str = ""  # "incident", "solution", "learning", "runbook"
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentMemory:
    """Memory system for an agent, combining short-term and long-term storage.

    Short-term memory is kept in-process (conversation turns).
    Long-term memory uses a simple in-memory store with tag-based retrieval
    (upgradeable to a vector store in Phase 3).

    Usage::

        memory = AgentMemory(agent_name="rca")

        # Store a learning
        memory.store(MemoryEntry(
            category="incident",
            content="Payment service outage caused by DB pool exhaustion",
            tags=["payment", "database", "pool"],
        ))

        # Retrieve relevant memories
        results = memory.search("database connection issues", limit=5)
    """

    def __init__(self, agent_name: str = "") -> None:
        self.agent_name = agent_name
        self._short_term: list[dict[str, str]] = []
        self._long_term: list[MemoryEntry] = []
        self._max_short_term: int = 50
        self._max_long_term: int = 10_000

    # ----- short-term memory -----

    def add_turn(self, role: str, content: str) -> None:
        """Add a conversation turn to short-term memory."""
        self._short_term.append({"role": role, "content": content})
        if len(self._short_term) > self._max_short_term:
            # Keep system + recent turns
            self._short_term = self._short_term[:1] + self._short_term[-(self._max_short_term - 1):]

    def get_conversation(self, *, limit: int = 20) -> list[dict[str, str]]:
        """Return recent conversation turns."""
        return self._short_term[-limit:]

    def clear_short_term(self) -> None:
        """Clear all short-term memory."""
        self._short_term.clear()

    # ----- long-term memory -----

    def store(self, entry: MemoryEntry) -> None:
        """Store an entry in long-term memory."""
        if not entry.id:
            entry.id = f"{self.agent_name}_{len(self._long_term):06d}"
        self._long_term.append(entry)

        if len(self._long_term) > self._max_long_term:
            self._long_term = self._long_term[-self._max_long_term:]

        logger.debug(
            "memory.stored",
            agent=self.agent_name,
            category=entry.category,
            tags=entry.tags,
        )

    def search(
        self,
        query: str,
        *,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search long-term memory using keyword and tag matching.

        This is a simple keyword-based search. In Phase 3, this will be
        replaced with semantic search using embeddings.

        Args:
            query: Search query string.
            category: Filter by category (optional).
            tags: Filter by tags (optional, any match).
            limit: Maximum results to return.

        Returns:
            A list of matching memory entries, scored by relevance.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        results: list[MemoryEntry] = []

        for entry in self._long_term:
            # Category filter
            if category and entry.category != category:
                continue

            # Tag filter (any match)
            if tags and not any(t in entry.tags for t in tags):
                continue

            # Simple keyword relevance scoring
            content_lower = entry.content.lower()
            score = 0.0
            for word in query_words:
                if word in content_lower:
                    score += 1.0
            if query_lower in content_lower:
                score += 3.0  # bonus for exact phrase match

            # Tag overlap bonus
            if tags:
                tag_overlap = len(set(tags) & set(entry.tags))
                score += tag_overlap * 2.0

            if score > 0:
                entry_copy = entry.model_copy()
                entry_copy.relevance_score = score
                results.append(entry_copy)

        # Sort by relevance, return top N
        results.sort(key=lambda e: e.relevance_score, reverse=True)
        return results[:limit]

    def get_all(self, *, category: str | None = None) -> list[MemoryEntry]:
        """Return all long-term memory entries, optionally filtered by category."""
        if category:
            return [e for e in self._long_term if e.category == category]
        return list(self._long_term)

    def clear_long_term(self) -> None:
        """Clear all long-term memory."""
        self._long_term.clear()

    def stats(self) -> dict[str, Any]:
        """Return memory usage statistics."""
        categories: dict[str, int] = {}
        for entry in self._long_term:
            categories[entry.category] = categories.get(entry.category, 0) + 1

        return {
            "agent": self.agent_name,
            "short_term_turns": len(self._short_term),
            "long_term_entries": len(self._long_term),
            "categories": categories,
        }
