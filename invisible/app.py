import logging

from fastapi import FastAPI


class TypedApp(FastAPI):
    logger = logging.Logger

    def __init__(self, **kwargs) -> None:
        super().__init__(docs_url=None, redoc_url="/docs", **kwargs)
        self.logger = logging.getLogger(self.title)
