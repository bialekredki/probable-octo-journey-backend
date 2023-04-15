from functools import partial

from nanoid import generate
from pydantic import AnyHttpUrl, Field, conint, constr, BaseModel, BaseConfig
from bson import ObjectId

from invisible.app import TypedApp


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
    tiny_url: constr(strip_whitespace=True, min_length=7, max_length=16)
    url: AnyHttpUrl = Field(...)
    max_redirects: conint(gt=0)
    time_to_live: conint(gt=0)

    class Config(ModelConfig):
        pass

def bootstrap_store(app: TypedApp):
    pass