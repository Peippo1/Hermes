from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .models import QueueItem


@dataclass
class SendQueue:
    items: list[QueueItem] = field(default_factory=list)

    def enqueue(self, item: QueueItem) -> QueueItem:
        self.items.append(item)
        return item

    def extend(self, items: Iterable[QueueItem]) -> list[QueueItem]:
        queued: list[QueueItem] = []
        for item in items:
            queued.append(self.enqueue(item))
        return queued

    def list_items(self) -> list[QueueItem]:
        return list(self.items)

