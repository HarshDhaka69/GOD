import time
from alphagram import Client, filters
from main import StartTime
from Database.users import get_all_users

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list: list[str] = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

@Client.on_message(filters.command("ping"))
async def ping(client, message):
    start_time = time.time()
    msg = await message.reply_text("🏓 ᴘɪɴɢɪɴɢ ʙᴀʙʏ....")
    end_time = time.time()
    telegram_ping = str(round((end_time - start_time) * 1000, 3)) + " ms"
    uptime = get_readable_time(time.time() - StartTime)
    u_c = len(await get_all_users())
    
    await msg.edit_text(
        f"ɪ ᴀᴍ ᴀʟɪᴠᴇ ʙᴀʙʏ! 🖤\n"
        f"<b>ᴛɪᴍᴇ ᴛᴀᴋᴇɴ:</b> <code>{telegram_ping}</code>\n"
        f"<b>ᴜᴘᴛɪᴍᴇ:</b> <code>{uptime}</code>\n"
        f"<b>ᴜsᴇʀs:</b> <code>{u_c}</code>"
    )