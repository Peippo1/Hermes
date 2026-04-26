from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .models import QueueItem


@dataclass
class SendQueue:
    items: list[QueueItem] = field(default_factory=list)
    _counter: int = 0

    def next_queue_id(self) -> str:
        self._counter += 1
        return f"QUEUE-{self._counter:04d}"

    def enqueue(self, item: QueueItem) -> QueueItem:
        if not item.queue_id:
            item = item.model_copy(update={"queue_id": self.next_queue_id()})
        self.items.append(item)
        return item

    def extend(self, items: Iterable[QueueItem]) -> list[QueueItem]:
        queued: list[QueueItem] = []
        for item in items:
            queued.append(self.enqueue(item))
        return queued

    def list_items(self) -> list[QueueItem]:
        return list(self.items)
