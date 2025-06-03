from . import db
from datetime import datetime, timezone
from typing import Optional, List, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = db.premium_users

async def add_premium(user_id: int, expiry_timestamp: datetime) -> bool:
    """Add or update premium user with expiry timestamp"""
    try:
        if not isinstance(expiry_timestamp, datetime):
            raise ValueError("expiry_timestamp must be a datetime object")
            
        await db.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'is_premium': True,
                    'expiry_date': expiry_timestamp,
                    'added_on': datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        logger.info(f"Added premium for user {user_id} until {expiry_timestamp}")
        return True
    except Exception as e:
        logger.error(f"Error adding premium user {user_id}: {e}")
        return False

async def remove_premium(user_id: int) -> bool:
    """Remove premium status from user"""
    try:
        result = await db.delete_one({'user_id': user_id})
        if result.deleted_count > 0:
            logger.info(f"Removed premium from user {user_id}")
            return True
        logger.warning(f"No premium record found for user {user_id}")
        return False
    except Exception as e:
        logger.error(f"Error removing premium user {user_id}: {e}")
        return False

async def is_premium(user_id: int) -> bool:
    """Check if user is premium and not expired"""
    try:
        user = await db.find_one({'user_id': user_id})
        if not user:
            return False
            
        # Check if premium has expired
        now = datetime.now(timezone.utc)
        if user['expiry_date'] < now:
            logger.info(f"Premium expired for user {user_id}")
            # Auto remove expired premium
            await remove_premium(user_id)
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error checking premium status for user {user_id}: {e}")
        return False

async def get_premium_expiry(user_id: int) -> Optional[datetime]:
    """Get premium expiry date for user"""
    try:
        user = await db.find_one({'user_id': user_id})
        if user:
            return user['expiry_date']
        return None
    except Exception as e:
        logger.error(f"Error getting premium expiry for user {user_id}: {e}")
        return None

async def get_all_premium_users() -> List[Dict]:
    """Get all premium users"""
    try:
        return await db.find({'is_premium': True}).to_list(length=None)
    except Exception as e:
        logger.error(f"Error getting all premium users: {e}")
        return []

async def get_active_premium_count() -> int:
    """Get count of active premium users"""
    try:
        now = datetime.now(timezone.utc)
        return await db.count_documents({
            'is_premium': True,
            'expiry_date': {'$gt': now}
        })
    except Exception as e:
        logger.error(f"Error getting active premium count: {e}")
        return 0

# Create indexes for better performance
async def create_indexes() -> None:
    try:
        await db.create_index('user_id', unique=True)
        await db.create_index('expiry_date')
        await db.create_index('is_premium')
        logger.info("Created premium database indexes")
    except Exception as e:
        logger.error(f"Error creating premium indexes: {e}") 