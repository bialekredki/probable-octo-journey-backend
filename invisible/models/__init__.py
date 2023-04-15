from datetime import datetime
from functools import partial

from bson import ObjectId
from nanoid import generate
from pydantic import AnyHttpUrl, BaseConfig, BaseModel, Field, NonNegativeInt

from invisible.app import TypedApp
from invisible.types import TinyURL


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class ModelConfig(BaseConfig):
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}    

class URL(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    tiny_url: TinyURL = Field(default_factory=partial(generate, size=16))
    url: AnyHttpUrl = Field(...)
    max_redirects: NonNegativeInt | None = None
    time_to_live: NonNegativeInt | None = None
    creation_time: datetime = Field(default_factory=datetime.now)
    last_visit_time: datetime | None = Field(default=None)

    class Config(ModelConfig):
        pass

def bootstrap_store(app: TypedApp):
    pass