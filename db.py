from config import Config
from motor.motor_asyncio import AsyncIOMotorClient

_client = AsyncIOMotorClient(Config.MONGO_URI)
db = _client[Config.MONGO_DB_NAME]