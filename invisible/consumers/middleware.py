import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Generator

import orjson
from aiokafka import ConsumerRecord

from invisible.consumers.utils import ParsedRecord, RecordT


class BaseMiddleware(ABC):
    @abstractmethod
    async def __call__(self, record: RecordT, stack: Generator) -> Any:
        raise NotImplementedError()

    def __str__(self) -> str:
        return self.__class__.__name__


class LoggingMiddleware(BaseMiddleware):
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    async def __call__(
        self, record: RecordT, stack: Generator[Any, Any, Coroutine]
    ) -> Any:
        self.logger.info("[%s]Received %s.", record.topic, record.value)
        await next(stack)(record, stack)


class ExceptionMiddleware(LoggingMiddleware):
    async def __call__(
        self, record: RecordT, stack: Generator[Any, Any, Coroutine]
    ) -> Any:
        try:
            await next(stack)(record, stack)
        except Exception as exc:
            self.logger.exception(
                "Exception %s while processsing message on topic %s", exc, record.topic
            )


class OrJSONMiddleware(BaseMiddleware):
    async def __call__(self, record: ConsumerRecord, stack: Generator) -> Any:
        await next(stack)(
            ParsedRecord(
                key=record.key,
                parition=record.partition,
                topic=record.topic,
                offset=record.offset,
                timestamp=record.timestamp,
                timestamp_type=record.timestamp_type,
                value=orjson.loads(record.value),
            ),
            stack,
        )
