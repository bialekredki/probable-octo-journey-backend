from pydantic import BaseModel, Field, AnyHttpUrl, NonNegativeInt


class CreateTinyURL(BaseModel):
    url: AnyHttpUrl = Field(..., description="A URL to be shortened.")
    max_redirects: NonNegativeInt | None = Field(None, description="Maximal number of redirects. After this number of redirects is reached tiny url won't work.")
    time_to_live: NonNegativeInt | None = Field(None, description="Time to live for tiny URL in hours.", alias="ttl")