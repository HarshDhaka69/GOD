from . import db

db = db.file_mapper

async def store_file(surl, chat_id, msg_ids: list[int]):
    await db.insert_one({"surl": surl, "chat_id": chat_id, "msg_ids": msg_ids})
    
async def get_file_loc(surl) -> tuple[int, list[int]]:
    '''
    Returns tuple[chat_id, list[msg_ids]]
    '''
    x = await db.find_one({"surl": surl})
    if x:
        return x["chat_id"], x["msg_ids"]
    return 0, 0