"""CSV and JSON file data connector.

Ingests local tabular metrics or log dumps from files for historical
replays, offline analysis, and test suites.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from opsbrain.connectors.base import ConnectorRecord, ConnectorStatus, DataConnector
from opsbrain.core.exceptions import ConnectorError


class CSVConnector(DataConnector):
    """Ingests operational data from local CSV or JSON files."""

    name = "csv_file"

    def __init__(self, file_path: str | Path, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.file_path = Path(file_path)

    async def connect(self) -> None:
        if not self.file_path.exists():
            self.status = ConnectorStatus.ERROR
            raise ConnectorError(f"File not found: {self.file_path}", connector="csv_file")
        self.status = ConnectorStatus.CONNECTED

    async def disconnect(self) -> None:
        self.status = ConnectorStatus.DISCONNECTED

    async def health_check(self) -> bool:
        return self.file_path.exists() and self.file_path.is_file()

    async def fetch(self, query: str = "", **kwargs: Any) -> list[ConnectorRecord]:
        """Read records from CSV or JSON file."""
        if not await self.health_check():
            raise ConnectorError(f"Target file {self.file_path} is inaccessible", connector="csv_file")

        records: list[ConnectorRecord] = []
        suffix = self.file_path.suffix.lower()

        if suffix == ".json":
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        records.append(
                            ConnectorRecord(
                                source=str(self.file_path.name),
                                record_type="json_entry",
                                payload=item if isinstance(item, dict) else {"value": item},
                            )
                        )
                elif isinstance(data, dict):
                    records.append(
                        ConnectorRecord(
                            source=str(self.file_path.name),
                            record_type="json_document",
                            payload=data,
                        )
                    )
        else:
            # Assume CSV
            with open(self.file_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(
                        ConnectorRecord(
                            source=str(self.file_path.name),
                            record_type="csv_row",
                            payload=dict(row),
                        )
                    )

        return records
