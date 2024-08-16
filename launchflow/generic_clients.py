from abc import ABC, abstractmethod


class PostgresClient(ABC):
    @abstractmethod
    def django_settings(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def sqlalchemy_engine_options(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def sqlalchemy_async_engine_options(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def sqlalchemy_engine(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def sqlalchemy_async_engine(self, *args, **kwargs):
        raise NotImplementedError


class RedisClient(ABC):
    @abstractmethod
    def django_settings(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def redis(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def redis_async(self, *args, **kwargs):
        raise NotImplementedError
