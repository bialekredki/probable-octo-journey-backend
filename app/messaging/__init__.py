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


async def send_message(producer: AIOKafkaProducer, action: str, data: BaseModel):
    await producer.send(
        __make_topic(data, action), orjson.dumps(data.dict(), default=_default_objectid)
    )
