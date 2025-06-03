from . import db
import datetime 

db = db.last_watched

async def set_last_watched_now(user_id: int) -> None:
    await db.update_one(
        {'user_id': user_id},
        {'$set': {'lw': datetime.datetime.now()}},
        upsert=True
    )

async def is_valid_to_watch(user_id: int, time: int = 86400) -> bool:
    x = await db.find_one({'user_id': user_id})
    if x and (datetime.datetime.now() - x['lw']).total_seconds() < 86400:
        return False
    return True