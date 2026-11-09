import logging
from typing import List, Optional, Dict, Any
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError, ConfigurationError
from app import config

logger = logging.getLogger(__name__)

# Single client instance with sensible timeouts
_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
            maxPoolSize=10,
        )
    return _client


def get_database():
    client = get_client()
    try:
        db = client.get_default_database()
        if db is not None:
            return db
    except ConfigurationError:
        pass
    return client[config.MONGO_DB_NAME]


def get_notifications_collection():
    db = get_database()
    return db["notifications"]


def check_db_health() -> bool:
    """Checks MongoDB connectivity via ping command."""
    try:
        client = get_client()
        client.admin.command("ping")
        return True
    except Exception as exc:
        logger.warning("MongoDB healthcheck failed: %s", exc)
        return False


def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to convert MongoDB _id to string for JSON serialization."""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def save_notification(event_data: Dict[str, Any]) -> str:
    """Inserts a notification document and returns its ID."""
    collection = get_notifications_collection()
    result = collection.insert_one(event_data)
    return str(result.inserted_id)


def list_notifications(limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
    """Retrieves recent notifications ordered by processed_at descending."""
    collection = get_notifications_collection()
    cursor = collection.find().sort("_id", DESCENDING).skip(skip).limit(limit)
    return [_serialize_doc(doc) for doc in cursor]


def get_notifications_by_user(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves notifications for a specific user_id."""
    collection = get_notifications_collection()
    cursor = (
        collection.find({"$or": [{"user_id": user_id}, {"cliente_id": user_id}]})
        .sort("_id", DESCENDING)
        .limit(limit)
    )
    return [_serialize_doc(doc) for doc in cursor]
