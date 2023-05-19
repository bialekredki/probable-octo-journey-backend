from typing import Any

import orjson
from aiokafka import AIOKafkaProducer
from bson import ObjectId
from pydantic import BaseModel


def __make_topic(model: BaseModel, action: str):
    return f"{model.__class__.__name__}.{action}"


def _default_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    raise TypeError()


async def send_message(
    producer: AIOKafkaProducer,
    action: str,
    data: BaseModel,
    *,
    additional_data: dict[str, Any] | None = None,
):
    topic = __make_topic(data, action)
    data: dict = data.dict()
    if additional_data:
        data.update(additional_data)
    await producer.send(topic, orjson.dumps(data, default=_default_objectid))
