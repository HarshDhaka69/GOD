from . import db
from datetime import datetime, timezone
from .premium import is_premium
import logging

logger = logging.getLogger(__name__)

db = db.usage

# Constants for daily limits
FREE_DAILY_LIMIT = 10
PREMIUM_DAILY_LIMIT = 99

async def get_usage(user_id: int) -> int:
    """Get user's daily usage count"""
    try:
        today = datetime.now(timezone.utc)
        today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        user = await db.find_one({
            'user_id': user_id,
            'date': today_start
        })
        return user['count'] if user else 0
    except Exception as e:
        logger.error(f"Error getting usage for user {user_id}: {e}")
        return 0

async def get_limit(user_id: int) -> int:
    """Get user's daily download limit"""
    try:
        if await is_premium(user_id):
            return PREMIUM_DAILY_LIMIT
        return FREE_DAILY_LIMIT
    except Exception as e:
        logger.error(f"Error getting limit for user {user_id}: {e}")
        return FREE_DAILY_LIMIT  # Default to free limit on error

async def incr_usage(user_id: int) -> bool:
    """Increment user's daily usage count"""
    try:
        today = datetime.now(timezone.utc)
        today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        result = await db.update_one(
            {
                'user_id': user_id,
                'date': today_start
            },
            {
                '$inc': {'count': 1}
            },
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"Error incrementing usage for user {user_id}: {e}")
        return False

async def reset_usage():
    """Reset usage counts older than 24 hours"""
    try:
        today = datetime.now(timezone.utc)
        today_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        await db.delete_many({'date': {'$lt': today_start}})
    except Exception as e:
        logger.error(f"Error resetting usage: {e}")

# Create indexes for better performance
async def create_indexes():
    try:
        await db.create_index([('user_id', 1), ('date', 1)], unique=True)
    except Exception as e:
        logger.error(f"Error creating usage indexes: {e}")