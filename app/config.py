from pydantic import BaseSettings, KafkaDsn, MongoDsn, PositiveInt, RedisDsn


class Configuration(BaseSettings):
    cache_ttl: PositiveInt = 2
    redis_dsn: RedisDsn = "redis://redis:6379"
    mongo_dsn: MongoDsn = "mongodb://mongo:mongo@mongo:27017"
    kafka_dsn: KafkaDsn = "kafka://kafka:9092"


configuration = Configuration()
