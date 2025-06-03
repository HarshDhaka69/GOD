from . import db

db = db.utr

async def add_utr(utr):
    await db.insert_one({"utr": utr})

async def is_utr_used(utr):
    return await db.find_one({"utr": utr})