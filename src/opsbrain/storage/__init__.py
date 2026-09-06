"""OpsBrain storage package."""

from opsbrain.storage.base import StorageBackend
from opsbrain.storage.sqlite import SQLiteStorage

__all__ = [
    "SQLiteStorage",
    "StorageBackend",
]
