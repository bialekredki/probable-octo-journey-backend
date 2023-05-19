import asyncio
import logging
from functools import partial
from typing import Any, Callable, Iterable

from aiokafka import AIOKafkaConsumer, ConsumerRecord

from app.consumers.handlers import BaseHandler
from app.consumers.middleware import BaseMiddleware


class Consumer:
    handlers: dict[str, list[Callable[[ConsumerRecord], Any]]]
    middleware: list[BaseMiddleware]
    logger: logging.Logger

    def __init__(self, bootstrap_servers, client_id, logger, services):
        self.logger = logger
        self.consumer = partial(
            AIOKafkaConsumer, bootstrap_servers=bootstrap_servers, client_id=client_id
        )
        self.handlers = {}
        self.middleware = []
        self.services = services or {}

    def declare_handler(self, handler: BaseHandler, topics: str | Iterable):
        topics = [topics] if isinstance(topics, str) else topics
        for topic in topics:
            if isinstance(handler, BaseHandler):
                handler.make_declared(self)
            self.handlers.setdefault(topic, [])
            self.handlers[topic].insert(0, handler)
            self.logger.info("Registered handler %s for topic %s", handler, topic)

    def declare_middleware(self, middleware: BaseMiddleware):
        self.middleware.insert(0, middleware)
        self.logger.info("Declared middleware %s.", middleware)

    def handle(self, record: ConsumerRecord, stack):
        return asyncio.gather(
            *[handler(record) for handler in self.handlers[record.topic]]
        )

    def stack(self):
        for middleware in self.middleware[1:]:
            yield middleware
        yield self.handle

    async def run(self):
        self.consumer = self.consumer(*list(self.handlers.keys()))
        await self.consumer.start()
        try:
            async for record in self.consumer:
                print(record)
                await self.middleware[0](record, self.stack())
        finally:
            await self.consumer.stop()
