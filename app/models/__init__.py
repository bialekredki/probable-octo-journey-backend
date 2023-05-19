from datetime import datetime, timedelta
from functools import partial

from bson import ObjectId
from nanoid import generate
from pydantic import AnyHttpUrl, BaseConfig, BaseModel, Field, NonNegativeInt

from app.app import TypedApp
from app.types import TinyURL


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
    last_modified_time: datetime | None = Field(default=None)

    @property
    def is_expired(self):
        return (
            self.time_to_live is not None
            and timedelta(hours=self.time_to_live)
            <= datetime.now() - self.creation_time
        )

    class Config(ModelConfig):
        pass
