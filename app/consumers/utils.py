from dataclasses import dataclass
from typing import Any, TypeVar

from aiokafka import ConsumerRecord


@dataclass(frozen=True)
class ParsedRecord:
    topic: str
    parition: int
    offset: int
    timestamp: int
    timestamp_type: int
    key: Any
    value: dict


RecordT = TypeVar("RecordT", ParsedRecord, ConsumerRecord)
