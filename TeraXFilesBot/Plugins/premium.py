from alphagram import Client, filters
from config import OWNER_ID
from Database.premium import add_premium, remove_premium, is_premium, get_premium_expiry
from datetime import datetime, timezone, timedelta
import re

# Command handler for adding premium users
@Client.on_message(filters.command("addpremium") & filters.user(OWNER_ID))
async def add_premium_user(_, message):
    """
    Add premium user with duration
    Format: /addpremium user_id duration
    Duration format: 1d, 1w, 1m, 1y
    """
    try:
        # Check command format
        args = message.text.split()
        if len(args) != 3:
            await message.reply("❌ Usage: /addpremium user_id duration\nExample: /addpremium 123456 30d")
            return

        # Parse user_id and duration
        try:
            user_id = int(args[1])
            duration_str = args[2].lower()
        except ValueError:
            await message.reply("❌ Invalid user ID")
            return

        # Parse duration
        match = re.match(r"(\d+)([dwmy])", duration_str)
        if not match:
            await message.reply("❌ Invalid duration format. Use: 1d, 1w, 1m, 1y")
            return

        amount = int(match.group(1))
        unit = match.group(2)

        # Calculate expiry date
        now = datetime.now(timezone.utc)
        if unit == 'd':
            expiry = now + timedelta(days=amount)
        elif unit == 'w':
            expiry = now + timedelta(weeks=amount)
        elif unit == 'm':
            expiry = now + timedelta(days=amount * 30)
        else:  # year
            expiry = now + timedelta(days=amount * 365)

        # Add premium
        if await add_premium(user_id, expiry):
            expiry_str = expiry.strftime("%Y-%m-%d %H:%M UTC")
            await message.reply(f"✅ Premium added successfully!\nUser ID: {user_id}\nExpires: {expiry_str}")
        else:
            await message.reply("❌ Failed to add premium user")

    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

# Command handler for removing premium users
@Client.on_message(filters.command("rmpremium") & filters.user(OWNER_ID))
async def remove_premium_user(_, message):
    """Remove premium status from user"""
    try:
        # Check command format
        args = message.text.split()
        if len(args) != 2:
            await message.reply("❌ Usage: /rmpremium user_id")
            return

        # Parse user_id
        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid user ID")
            return

        # Remove premium
        if await remove_premium(user_id):
            await message.reply(f"✅ Premium removed successfully from user {user_id}")
        else:
            await message.reply("❌ Failed to remove premium status")

    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

# Command for users to check their premium status
@Client.on_message(filters.command("premium"))
async def check_premium(_, message):
    """Check premium status and expiry"""
    user_id = message.from_user.id
    
    if not await is_premium(user_id):
        await message.reply("ℹ️ You are not a premium user.\n\nPremium Benefit:\n- 99 downloads per day\n\nUse /plans to view premium plans.")
        return
        
    expiry = await get_premium_expiry(user_id)
    if expiry:
        expiry_str = expiry.strftime("%Y-%m-%d %H:%M UTC")
        remaining = expiry - datetime.now(timezone.utc)
        days = remaining.days
        
        await message.reply(
            f"✨ You are a premium user!\n\n"
            f"Expiry Date: {expiry_str}\n"
            f"Days Remaining: {days}\n\n"
            f"Premium Benefit:\n"
            f"- 99 downloads per day"
        ) 