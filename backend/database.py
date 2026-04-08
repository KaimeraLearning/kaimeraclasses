"""Shared database connection and utilities"""
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
