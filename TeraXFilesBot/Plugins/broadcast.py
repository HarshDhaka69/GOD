from alphagram import Client, filters
from alphagram.types import InlineKeyboardButton, InlineKeyboardMarkup
from Database.users import get_all_users
from config import OWNER_ID

sent = 0
failed = 0
running = False

markup = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton('Progress', callback_data='bcprogress')]
    ]
)

@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(_, m):
    global sent, failed, running
    if running:
        return await m.reply('Broadcast is already ongoing.', reply_markup=markup)
    if not m.reply_to_message:
        return await m.reply("Usage: /broadcast [options] and reply to a message.\n\nOptions:\n-nf: No Forward.")
    sent = failed = 0
    ok = await m.reply("Broadcasting...", reply_markup=markup)
    running = True
    if "-nf" in m.text:
        for user in await get_all_users():
            try:
                await m.reply_to_message.copy(user)
                sent += 1
            except:
                failed += 1
                pass
    else:
        for user in await get_all_users():
            try:
                await m.reply_to_message.forward(user)
                sent += 1
            except:
                failed += 1
                pass
    running = False
    try:
        await ok.edit(f"Broadcast Complete\n\nSent To: `{sent}`\nFailed: `{failed}`")
    except:
        pass

@Client.on_callback_query(filters.regex('^bcprogress$'))
async def bc_cbq(_, q):
    if not running:
        return await q.answer('No Broadcast is going on.', show_alert=True)
    txt = f'Sent: {sent}\nFailed: {failed}'
    return await q.answer(txt, show_alert=True)