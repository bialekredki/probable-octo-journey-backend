import logging

from app.consumers import Consumer
from app.consumers.middleware import BaseMiddleware, Generator, ParsedRecord, RecordT


class CountingMiddleware(BaseMiddleware):
    class_counter = 0

    def __init__(self) -> None:
        self.counter = 0

    async def __call__(self, record: RecordT, stack: Generator):
        self.counter += 1
        CountingMiddleware.class_counter += 1
        await next(stack)(record, stack)


async def test_middleware_stack():
    consumer = Consumer(None, None, logger=logging.getLogger(), services={})
    for _ in range(10):
        consumer.declare_middleware(CountingMiddleware())

    async def handler(_):
        pass

    consumer.declare_handler(handler, [None])
    record = ParsedRecord(None, None, None, None, None, None, None)
    await consumer.middleware[0](record, consumer.stack())
    assert CountingMiddleware.class_counter == 10
    assert all(middleware.counter == 1 for middleware in consumer.middleware)
