from alphagram import Client, filters
from Database.users import add_user, is_user
from Database.last_watched import set_last_watched_now
from Database.premium import add_premium, is_premium, get_premium_expiry
from Database.usage import FREE_DAILY_LIMIT, PREMIUM_DAILY_LIMIT
from config import START_IMG, SUPPORT_URL, UPDATE_URL, OWNER_ID
from alphagram.types import InlineKeyboardMarkup as IKM, InlineKeyboardButton as IKB
from .download import get_token, reset_token
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

@Client.on_message(filters.command('start') & filters.private)
async def start(_, m):
    try:
        user_id = m.from_user.id
        if not await is_user(user_id):
            await add_user(user_id)
        
        if "ads_" in m.text and get_token(user_id):
            token = m.text.split("ads_")[1]
            if token != get_token(user_id):
                return await m.reply("Invalid Token.")
            await m.reply("Task done.")
            await set_last_watched_now(user_id)
            reset_token(user_id)
            return

        # Check premium status with proper error handling
        try:
            is_premium_user = await is_premium(user_id)
            status_text = "Premium User 👑" if is_premium_user else "Free User ⭐"
            daily_limit = PREMIUM_DAILY_LIMIT if is_premium_user else FREE_DAILY_LIMIT
        except Exception as e:
            logger.error(f"Error checking premium status: {e}")
            is_premium_user = False
            status_text = "Free User ⭐"
            daily_limit = FREE_DAILY_LIMIT

        buttons = IKM([
            [IKB("Support", url=SUPPORT_URL), IKB("Updates", url=UPDATE_URL)],
            [IKB("My Plan 📊", callback_data="my_plan"), IKB("Get Premium 👑", callback_data="show_plans")]
        ])

        await m.reply_photo(
            photo=START_IMG,
            caption=f"**𝐇𝐞𝐥𝐥𝐨! 𝐈 𝐚𝐦 𝐓𝐞𝐫𝐚𝐛𝐨𝐱 𝐕𝐢𝐝𝐞𝐨 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭.**\n\n"
                   f"𝐒𝐞𝐧𝐝 𝐦𝐞 𝐭𝐞𝐫𝐚𝐛𝐨𝐱 𝐯𝐢𝐝𝐞𝐨 𝐥𝐢𝐧𝐤 & 𝐈 𝐰𝐢𝐥𝐥 𝐬𝐞𝐧𝐝 𝐕𝐢𝐝𝐞𝐨.",
            reply_markup=buttons
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await m.reply("An error occurred. Please try again later.")

@Client.on_callback_query(filters.regex("^show_plans$"))
async def show_plans(_, query):
    from .buy import markup  # Import the premium plans markup
    await query.message.edit_text(
        "🌟 Premium Plans\n\n"
        "Benefits:\n"
        "- 99 downloads per day\n\n"
        "Choose a plan:",
        reply_markup=markup
    )

@Client.on_callback_query(filters.regex("^my_plan$"))
async def my_plan(_, query):
    user_id = query.from_user.id
    is_premium_user = await is_premium(user_id)
    status = "Premium" if is_premium_user else "Free"
    daily_limit = PREMIUM_DAILY_LIMIT if is_premium_user else FREE_DAILY_LIMIT
    
    plan_text = f"**Your Current Plan**\n\n"
    plan_text += f"Status: {status} User\n"
    plan_text += f"Daily Download Limit: {daily_limit}\n"
    
    if is_premium_user:
        expiry = await get_premium_expiry(user_id)
        plan_text += f"Premium Expires: {expiry.strftime('%Y-%m-%d %H:%M UTC')}"
    else:
        plan_text += f"\nUpgrade to Premium to get:\n- {PREMIUM_DAILY_LIMIT} downloads per day\n- No ads required"

    buttons = IKM([
        [IKB("Get Premium 👑", callback_data="show_plans")],
        [IKB("🔙 Back", callback_data="back_to_start")]
    ])
    
    await query.message.edit_text(plan_text, reply_markup=buttons)

@Client.on_callback_query(filters.regex("^back_to_start$"))
async def back_to_start(_, query):
    user_id = query.from_user.id
    is_premium_user = await is_premium(user_id)
    status_text = "Premium User 👑" if is_premium_user else "Free User ⭐"
    daily_limit = PREMIUM_DAILY_LIMIT if is_premium_user else FREE_DAILY_LIMIT

    buttons = IKM([
        [IKB("Support", url=SUPPORT_URL), IKB("Updates", url=UPDATE_URL)],
        [IKB("My Plan 📊", callback_data="my_plan"), IKB("Get Premium 👑", callback_data="show_plans")]
    ])

    await query.message.edit_photo(
        photo=START_IMG,
        caption=f"**𝐇𝐞𝐥𝐥𝐨! 𝐈 𝐚𝐦 𝐓𝐞𝐫𝐚𝐛𝐨𝐱 𝐕𝐢𝐝𝐞𝐨 𝐃𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐞𝐫 𝐁𝐨𝐭.**\n\n"
               f"Your Status: {status_text}\n"
               f"Daily Limit: {daily_limit} downloads\n\n"
               f"𝐒𝐞𝐧𝐝 𝐦𝐞 𝐭𝐞𝐫𝐚𝐛𝐨𝐱 𝐯𝐢𝐝𝐞𝐨 𝐥𝐢𝐧𝐤 & 𝐈 𝐰𝐢𝐥𝐥 𝐬𝐞𝐧𝐝 𝐕𝐢𝐝𝐞𝐨.",
        reply_markup=buttons
    )

@Client.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium_cmd(_, m):
    try:
        # Command format: /addpremium [user_id] [days]
        parts = m.text.split()
        if len(parts) != 3:
            return await m.reply("❌ Usage: /addpremium [user_id] [days]")
        
        user_id = int(parts[1])
        days = int(parts[2])
        
        # Calculate new expiry
        now = datetime.now(timezone.utc)
        current_expiry = await get_premium_expiry(user_id)
        
        if current_expiry and current_expiry > now:
            new_expiry = current_expiry + timedelta(days=days)
        else:
            new_expiry = now + timedelta(days=days)
        
        # Add premium
        if await add_premium(user_id, new_expiry):
            await m.reply(
                f"✅ Successfully added {days} days of premium!\n\n"
                f"User ID: {user_id}\n"
                f"Expires: {new_expiry.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            # Notify the user
            try:
                await _.send_message(
                    user_id,
                    f"🎉 You've been granted {days} days of premium!\n\n"
                    f"Expiry: {new_expiry.strftime('%Y-%m-%d %H:%M UTC')}\n"
                    f"Daily Downloads: {PREMIUM_DAILY_LIMIT}"
                )
            except:
                pass
        else:
            await m.reply("❌ Failed to add premium. Please try again.")
            
    except ValueError:
        await m.reply("❌ Invalid input. User ID and days must be numbers.")
    except Exception as e:
        await m.reply(f"❌ Error: {str(e)}")