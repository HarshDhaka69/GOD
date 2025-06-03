from alphagram import Client, filters
from alphagram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup as IKM
from datetime import datetime, timedelta, timezone
import aiohttp
import qrcode
import os

# Database imports
from Database.premium import add_premium, is_premium, get_premium_expiry
from Database.utr import is_utr_used, add_utr

# Config
from config import UPI_ID, BP_API_URL

def get_qr(price: int, user_id: int) -> str:
    """Generate QR code for payment"""
    path = f'DL/{user_id}_qr.png'
    url = f"upi://pay?pa={UPI_ID}&pn=Harsh&am={price}&cu=INR&tn={user_id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill="black", back_color="white")
    img.save(path)
    return path

# Premium plan prices and durations
PLANS = {
    "50": {"days": 15, "price": 50},
    "100": {"days": 30, "price": 100}
}

markup = IKM([
    [IKB("15 Days - 50₹", callback_data="buy_50")],
    [IKB("30 Days - 100₹", callback_data="buy_100")]
])

@Client.on_message(filters.command("plans") & filters.private)
async def plans_cmd(_, message):
    """Show available premium plans"""
    user_id = message.from_user.id
    is_premium_user = await is_premium(user_id)
    
    if is_premium_user:
        expiry = await get_premium_expiry(user_id)
        expiry_str = expiry.strftime("%Y-%m-%d %H:%M UTC")
        await message.reply(
            f"You already have premium access until {expiry_str}!\n\n"
            f"To extend your premium duration, you can purchase another plan:"
        )
    
    await message.reply(
        "🌟 Premium Plans\n\n"
        "Benefits:\n"
        "- 99 downloads per day\n\n"
        "Choose a plan:",
        reply_markup=markup
    )

@Client.on_callback_query(filters.regex("^buy_[0-9]+$"))
async def buy_callback(_, query):
    """Handle plan selection"""
    plan_price = query.data.split('_')[1]
    if plan_price not in PLANS:
        await query.answer("Invalid plan selected!", show_alert=True)
        return
        
    plan = PLANS[plan_price]
    caption = (
        f"💳 Payment Details\n\n"
        f"Amount: ₹{plan['price']}\n"
        f"Duration: {plan['days']} days\n"
        f"Daily Downloads: 99\n\n"
        f"Scan QR code to pay. After payment, send:\n"
        f"`/verify YOUR_UTR_NUMBER`\n\n"
        f"Example: `/verify 123456789012`"
    )
    
    qr_path = get_qr(plan['price'], query.from_user.id)
    await query.message.reply_photo(
        photo=qr_path,
        caption=caption
    )
    try:
        os.remove(qr_path)
    except:
        pass
    await query.answer()

@Client.on_message(filters.command("verify") & filters.private)
async def verify_payment(_, message):
    """Verify payment and activate premium"""
    user_id = message.from_user.id
    msg = await message.reply("🔄 Validating payment...")
    
    try:
        utr = message.text.split()[1]
        if not utr.isdigit():
            raise ValueError
    except:
        return await msg.edit("❌ Usage: /verify YOUR_UTR_NUMBER")
        
    # Check if UTR already used
    if await is_utr_used(utr):
        return await msg.edit("❌ This payment has already been used!")
        
    # Verify payment
    async with aiohttp.ClientSession() as session:
        async with session.get(BP_API_URL + str(utr)) as resp:
            if resp.status != 200:
                return await msg.edit("❌ Invalid UTR number!")
            data = await resp.json()
            
    if "amount" not in data:
        return await msg.edit("❌ Invalid payment details!")
        
    amount = int(data["amount"])
    if str(amount) not in PLANS:
        return await msg.edit("❌ Invalid payment amount!")
        
    # Calculate new expiry
    plan = PLANS[str(amount)]
    now = datetime.now(timezone.utc)
    
    # If user already has premium, extend from current expiry
    current_expiry = await get_premium_expiry(user_id)
    if current_expiry and current_expiry > now:
        new_expiry = current_expiry + timedelta(days=plan['days'])
    else:
        new_expiry = now + timedelta(days=plan['days'])
    
    # Add premium and mark UTR as used
    if await add_premium(user_id, new_expiry):
        await add_utr(utr)
        await msg.edit(
            f"✅ Payment verified!\n\n"
            f"Premium activated until: {new_expiry.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Daily download limit: 99"
        )
    else:
        await msg.edit("❌ Failed to activate premium. Please contact support.")
