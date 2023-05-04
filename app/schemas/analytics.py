from pydantic import BaseModel, Field, NonNegativeInt
from datetime import date


class AnalyticsStatsItem(BaseModel):
    visits: NonNegativeInt = Field(
        ..., description="Number of visits in given time range."
    )
    unqiue_visits: NonNegativeInt = Field(
        ...,
        description="Number of unique vistis in a given timerange. A unique visit is defined as a group of visit done from a single IP address with the same device(model, OS and browser).",
    )
    day: date = Field(..., description="A date.")
