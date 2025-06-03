from . import db

db = db.ads

async def set_ads_token(user_id: int, ads_token: str) -> None:
    await db.update_one(
        {'user_id': user_id},
        {'$set': {'ads_token': ads_token}},
        upsert=True
    )

async def get_ads_token(user_id: int) -> str | None:
    x = await db.find_one({'user_id': user_id})
    if x:
        return x['ads_token']
    

async def del_ads_token(user_id: int) -> None:
    await db.delete_one({'user_id': user_id})