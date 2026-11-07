from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings


@lru_cache
def get_client() -> MongoClient:
    return MongoClient(settings.mongo_uri)


def get_db() -> Database:
    return get_client().get_default_database(settings.database_name)
