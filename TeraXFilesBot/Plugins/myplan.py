from alphagram import Client, filters
import logging

# Database imports
from Database.usage import get_usage, get_limit, FREE_DAILY_LIMIT, PREMIUM_DAILY_LIMIT
from Database.premium import is_premium, get_premium_expiry

# Config
from config import UPDATE

# Configure logger
logger = logging.getLogger(__name__)

@Client.on_message(filters.command("myplan") & filters.private)
async def myplan(_, m):
    try:
        user_id = m.from_user.id
        is_premium_user = await is_premium(user_id)
        usage = await get_usage(user_id)
        limit = await get_limit(user_id)

        # Get premium expiry if user is premium
        expiry_text = ""
        if is_premium_user:
            expiry = await get_premium_expiry(user_id)
            if expiry:
                expiry_text = f"\n**⏳ Premium Expires:** {expiry.strftime('%Y-%m-%d %H:%M UTC')}"

        plan_status = "✅ **Premium**" if is_premium_user else "❌ **Free**"
        downloads_text = f"**{usage}/{limit}** downloads today"

        benefits_text = ""
        if not is_premium_user:
            benefits_text = (
                f"\n\n**💎 Premium Benefits:**\n"
                f"• {PREMIUM_DAILY_LIMIT} downloads per day\n"
                f"• No ads required\n"
                f"• Priority support\n\n"
                f"Use /plans to view premium plans!"
            )

        await m.reply_text(
            f"**📜 Your Plan Details:**\n\n"
            f"**👤 User ID:** `{user_id}`\n"
            f"**💎 Plan:** {plan_status}\n"
            f"**📥 Usage:** {downloads_text}{expiry_text}{benefits_text}\n\n"
            f"**Powered by @{UPDATE}**"
        )
    except Exception as e:
        logger.error(f"Error in myplan command for user {m.from_user.id}: {e}")
        await m.reply("An error occurred while fetching your plan details. Please try again later.")