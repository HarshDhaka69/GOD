from . import db
from datetime import datetime
from typing import List, Dict, Optional

db = db.users

async def is_user(user_id: int) -> bool:
    try:
        return bool(await db.find_one({'user_id': user_id}))
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False

async def add_user(user_id: int) -> bool:
    try:
        if await is_user(user_id):
            return True
        await db.insert_one({'user_id': user_id, 'end': None})
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

async def get_all_users() -> List[int]:
    try:
        return [x['user_id'] for x in await (db.find()).to_list(None)]
    except Exception as e:
        print(f"Error getting all users: {e}")
        return []

async def get_all_raw_users() -> List[Dict]:
    try:
        return await (db.find()).to_list(None)
    except Exception as e:
        print(f"Error getting raw users: {e}")
        return []

async def set_premium(user_id: int, dt_object: datetime) -> bool:
    try:
        await db.update_one(
            {'user_id': user_id},
            {'$set': {'end': dt_object}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error setting premium: {e}")
        return False

async def get_premium(user_id: int) -> Optional[datetime]:
    try:
        user = await db.find_one({'user_id': user_id})
        return user['end'] if user else None
    except Exception as e:
        print(f"Error getting premium status: {e}")
        return None

# Create indexes for better performance
async def create_indexes():
    try:
        await db.create_index('user_id', unique=True)
        await db.create_index('end')
    except Exception as e:
        print(f"Error creating indexes: {e}")