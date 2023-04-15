from pydantic import BaseSettings, RedisDsn, MongoDsn


class Configuration(BaseSettings):
    redis_dsn: RedisDsn = "redis://redis:6379"
    mongo_dsn: MongoDsn = "mongodb://mongo:mongo@mongo:27017"

configuration = Configuration()