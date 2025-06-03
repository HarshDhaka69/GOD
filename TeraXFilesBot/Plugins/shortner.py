from Database.ads_shortner import (
    enable_feature, disable_feature, is_disabled,
    # For backward compatibility
    enable_shortner, disable_shortner, is_shortner_disabled
)
from alphagram import Client, filters # type: ignore
from alphagram.types import InlineKeyboardButton, InlineKeyboardMarkup # type: ignore
from config import OWNER_ID, SHORTNER_API_URL
import requests # type: ignore

@Client.on_message(filters.command('settings') & filters.user(OWNER_ID))
async def shortner(_, m):
    is_feature_disabled = await is_disabled()
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('Ads/Shortner', callback_data='answer'),
                InlineKeyboardButton('Disabled ❌' if is_feature_disabled else 'Enabled ✅', callback_data='toggle')
            ]
        ]
    )
    return await m.reply('Settings', reply_markup=markup)

@Client.on_callback_query(filters.regex('^toggle$'))
async def toggle_cbq(_, q):
    is_feature_disabled = await is_disabled()
    await enable_feature() if is_feature_disabled else await disable_feature()
    is_feature_disabled = not is_feature_disabled
    
    markup = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton('Ads/Shortner', callback_data='answer'),
                InlineKeyboardButton('Disabled ❌' if is_feature_disabled else 'Enabled ✅', callback_data='toggle')
            ]
        ]
    )
    await q.answer()
    await q.edit_message_reply_markup(markup)

def generate_short_link(actual_link: str) -> str:
    x = requests.get(SHORTNER_API_URL + actual_link)
    return x.json()['shortenedUrl']