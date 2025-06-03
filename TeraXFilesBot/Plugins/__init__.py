info = None

async def bot_info(_):
    global info
    if not info:
        info = await _.get_me()
    return info