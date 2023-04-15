import logging

from fastapi import FastAPI


class TypedApp(FastAPI):
    logger = logging.Logger
