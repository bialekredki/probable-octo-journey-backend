from pydantic import AnyHttpUrl, BaseModel, Field, NonNegativeInt, PositiveInt, constr

from app.models import ModelConfig, PyObjectId


class Path(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    url: AnyHttpUrl
    redirects: NonNegativeInt = 0
    tiny_urls: PositiveInt = 1

    class Config(ModelConfig):
        pass


class Host(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    host: constr(strip_whitespace=True, strict=True, min_length=2, max_length=2**10)
    paths_ids: list[PyObjectId]
    total_redirects: NonNegativeInt = 0
    total_tiny_urls: PositiveInt = 1

    class Config(ModelConfig):
        pass
