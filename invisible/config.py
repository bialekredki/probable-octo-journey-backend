from pydantic import BaseSettings, RedisDsn, MongoDsn, PositiveInt


class Configuration(BaseSettings):
    cache_ttl: PositiveInt = 2
    redis_dsn: RedisDsn = "redis://redis:6379"
    mongo_dsn: MongoDsn = "mongodb://mongo:mongo@mongo:27017"


configuration = Configuration()
