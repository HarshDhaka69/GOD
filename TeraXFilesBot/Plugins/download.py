from alphagram import Client, filters
from config import TERABOX_API_URL, TERABOX_API_TOKEN, VIDEO_STORE_GROUP_ID, FSUB_ID, FSUB_INVITE_LINK, UPDATE, OWNER_ID
import aiohttp, asyncio, os, sys, glob, gc, time, logging, uuid
from typing import Optional, Dict, Any
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
import aiofiles
from moviepy import VideoFileClip

# Database imports
from Database.usage import get_usage, get_limit, incr_usage
from Database.last_watched import is_valid_to_watch
from Database.file_mapper import get_file_loc, store_file
from Database.ads_shortner import is_disabled as is_ad_disabled
from Database.premium import is_premium

# Local imports
from .utils import format_size
from .shortner import generate_short_link
from main import app

# Telegram types
from alphagram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure process pool for CPU-intensive tasks
CPU_COUNT = multiprocessing.cpu_count()
PROCESS_POOL = ThreadPoolExecutor(max_workers=CPU_COUNT)

# Optimize for NVMe SSD
CHUNK_SIZE = 50 * 1024 * 1024  # 50MB chunks for NVMe
BUFFER_SIZE = 8 * 1024 * 1024  # 8MB buffer for file operations

# Configure download settings
MAX_CONCURRENT_DOWNLOADS = 3
DOWNLOAD_SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
UPDATE_INTERVAL = 3  # Update progress every 3 seconds

def get_progress_bar(current, total, length=10):
    """Generate a star-based progress bar"""
    progress = int(length * current / total)
    return "★" * progress + "☆" * (length - progress)

async def update_progress_message(message, filename, current, total, user_id, username, speed=0, status="Downloading"):
    """Update progress message with fancy formatting"""
    try:
        progress = (current / total) * 100
        progress_bar = get_progress_bar(current, total)
        
        status_text = (
            f"┏ ғɪʟᴇɴᴀᴍᴇ: {filename}\n"
            f"┠ [{progress_bar}] {progress:.2f}%\n"
            f"┠ ᴘʀᴏᴄᴇssᴇᴅ: {format_size(current)} ᴏғ {format_size(total)}\n"
            f"┠ sᴛᴀᴛᴜs: {status}\n"
            f"┠ sᴘᴇᴇᴅ: {format_size(speed)}/s\n"
            f"┖ ᴜsᴇʀ: {username} | ɪᴅ: {user_id}"
        )
        
        await message.edit_text(status_text)
    except Exception as e:
        logger.error(f"Error updating progress: {e}")

async def download_with_progress(url: str, user_id: int, message, filename: str, username: str):
    path = f'DL/{user_id}.mp4'
    last_update_time = 0
    last_downloaded = 0
    max_retries = 3
    retry_delay = 5  # seconds
    
    async with DOWNLOAD_SEMAPHORE:
        for attempt in range(max_retries):
            try:
                connector = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
                timeout = aiohttp.ClientTimeout(total=3600)
                
                async with aiohttp.ClientSession(
                    timeout=timeout,
                    connector=connector,
                    raise_for_status=False  # Don't raise for status automatically
                ) as session:
                    async with session.get(url) as resp:
                        if resp.status == 503:
                            if attempt < max_retries - 1:
                                await message.edit(f"Server busy (503). Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(retry_delay)
                                continue
                            else:
                                raise aiohttp.ClientError(f"Service unavailable after {max_retries} attempts")
                        
                        resp.raise_for_status()  # Now raise for other status codes
                        total = int(resp.headers.get('content-length', 0))
                        downloaded = 0
                        
                        async with aiofiles.open(path, 'wb', buffering=BUFFER_SIZE) as f:
                            async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                                if not chunk:  # Check for empty chunk
                                    raise aiohttp.ClientError("Empty response from server")
                                await f.write(chunk)
                                downloaded += len(chunk)
                                current_time = time.time()
                                
                                if current_time - last_update_time >= UPDATE_INTERVAL:
                                    speed = (downloaded - last_downloaded) / (current_time - last_update_time)
                                    await update_progress_message(
                                        message, 
                                        filename, 
                                        downloaded, 
                                        total, 
                                        user_id,
                                        username,
                                        speed
                                    )
                                    last_update_time = current_time
                                    last_downloaded = downloaded
                        
                        # If we get here, download was successful
                        return path
                        
            except aiohttp.ClientError as e:
                if attempt < max_retries - 1:
                    error_msg = str(e)
                    if "503" in error_msg:
                        await message.edit(f"Server busy (503). Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    else:
                        await message.edit(f"Download failed. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    raise  # Re-raise the last error if all retries failed
            except Exception as e:
                raise  # Re-raise any other exceptions immediately
    
    raise aiohttp.ClientError("Download failed after all retries")

async def fetch_json(url: str) -> dict:
    connector = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(url) as resp:
            return await resp.json()

async def download_thumb(url: str, user_id: int) -> Optional[str]:
    path = f'DL/{user_id}.jpg'
    connector = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(
        timeout=timeout,
        connector=connector,
        raise_for_status=True
    ) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(path, 'wb', buffering=BUFFER_SIZE) as f:
                    await f.write(await resp.read())
                return path
            return None

def extract_video_info(path: str) -> dict:
    """Extract video information in a separate thread"""
    with VideoFileClip(path) as clip:
        return {
            'duration': int(clip.duration),
            'width': int(clip.w),
            'height': int(clip.h)
        }

async def download(url: str, user_id: int) -> str:
    path = f'DL/{user_id}.mp4'
    
    async with DOWNLOAD_SEMAPHORE:  # Limit concurrent downloads
        connector = aiohttp.TCPConnector(limit=None, ttl_dns_cache=300)
        timeout = aiohttp.ClientTimeout(total=3600)
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            raise_for_status=True
        ) as session:
            async with session.get(url) as resp:
                async with aiofiles.open(path, 'wb', buffering=BUFFER_SIZE) as f:
                    downloaded = 0
                    async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        downloads_manager[user_id]['downloaded'] = downloaded
    
    return path

ads: dict = {} # user_id: secret_key

def get_token(user_id):
    return ads.get(user_id)
    
def reset_token(user_id):
    if user_id in ads:
        del ads[user_id]
            
def generate(user_id, bot_username):
    ads[user_id] = str(uuid.uuid4())
    url = generate_short_link(f"https://t.me/{bot_username}?start=ads_{ads[user_id]}")
    return InlineKeyboardMarkup([[InlineKeyboardButton("Proceed", url=url)]])
    
fsub_markup = InlineKeyboardMarkup([
    [InlineKeyboardButton("Join Channel", url=FSUB_INVITE_LINK)],
    [InlineKeyboardButton("Try Again", callback_data="try_again")]
])

async def is_valid_to_dl(_, user_id: int) -> tuple[bool, str, None]:
    if user_id in downloads_manager:
        return False, 'Already downloading something...', None
        
    # Check premium status first
    is_premium_user = await is_premium(user_id)
    
    # Skip ad check for premium users
    if not is_premium_user and not await is_ad_disabled():
        if await is_valid_to_watch(user_id):
            return False, "You've to watch an ad to proceed for next 24 hours.", generate(user_id, _.me.username)
            
    # Check force subscribe
    try:
        if (await _.get_chat_member(FSUB_ID, user_id)).status.name not in ["MEMBER", "ADMINISTRATOR", "OWNER"]:
            return False, "**👋 Hello!**\n\n**Please join our channel to use the bot.**\n**Click below to join.**", fsub_markup
    except:
        return False, "**👋 Hello!**\n\n**Please join our channel to use the bot.**\n**Click below to join.**", fsub_markup
        
    # Check usage limits
    current_usage = await get_usage(user_id)
    daily_limit = await get_limit(user_id)
    
    if current_usage >= daily_limit:
        if is_premium_user:
            return False, f'You have reached your daily limit of `{daily_limit}` downloads. Try again tomorrow.', None
        else:
            return False, f'You have reached daily limit of `{daily_limit}` downloads. Get premium for 99 daily downloads using /plans.', None
            
    return True, '', None

downloads_manager: Dict[int, Dict[str, Any]] = {}

# Remove old markup with progress button
markup = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton('Cancel', callback_data='cancel')]
    ]
)

def cback(current, total, uid):
    downloads_manager[uid]['size'] = total
    downloads_manager[uid]['downloaded'] = current

@Client.on_message(filters.private, group=1)
async def dl(_, m: Message):
    user_id = m.from_user.id
    username = m.from_user.first_name
    status_msg = None
    
    try:
        if not m.text or not m.text.startswith('https://'):
            return await m.reply('Invalid URL.')
            
        url = m.text
        if '/s/' not in url:
            return await m.reply('Invalid URL.')
            
        # Check force subscribe first
        try:
            if (await _.get_chat_member(FSUB_ID, user_id)).status.name not in ["MEMBER", "ADMINISTRATOR", "OWNER"]:
                mention = f"[{username}](tg://user?id={user_id})"
                return await m.reply(
                    f"**👋 Hello {mention}!**\n\n**Please join our channel to use the bot.**\n**Click below to join.**",
                    reply_markup=fsub_markup
                )
        except:
            mention = f"[{username}](tg://user?id={user_id})"
            return await m.reply(
                f"**👋 Hello {mention}!**\n\n**Please join our channel to use the bot.**\n**Click below to join.**",
                reply_markup=fsub_markup
            )
            
        status_msg = await m.reply('Processing download...')
        surl = url.split('/s/')[1]
        
        try:
            loc = list(await get_file_loc(surl))
        except Exception as e:
            logger.error(f"Error checking file location: {e}")
            return await status_msg.edit("Error checking file cache. Please try again.")
            
        if loc[0] != 0:
            try:
                await status_msg.edit('Sending cached file...')
                messages = await _.get_messages(*loc)
                for msg in messages:
                    x = await is_valid_to_dl(_, user_id)
                    if not x[0]:
                        return await status_msg.edit(x[1], reply_markup=x[2])
                    sent = await msg.copy(user_id)
                    if not await is_ad_disabled():
                        asyncio.create_task(delete_message_after(_, user_id, sent.id, 600))
                    await incr_usage(user_id)
                await status_msg.delete()
                return
            except Exception as e:
                logger.error(f"Error sending cached file: {e}")
                # If cached file send fails, continue to fresh download
                
        # Fresh download from Terabox
        try:
            resp = await fetch_json(TERABOX_API_URL + f'/url?token={TERABOX_API_TOKEN}&url={url}')
            if not resp or not isinstance(resp, list):
                logger.error(f"Invalid response from Terabox API: {resp}")
                return await status_msg.edit("Error: Invalid response from Terabox API. Please try again later.")
        except Exception as e:
            logger.error(f"Terabox API error: {e}")
            return await status_msg.edit("Error fetching file information from Terabox. Please try again later.")
            
        if not resp:
            return await status_msg.edit("No files found or invalid Terabox link.")
            
        ids = []
        for c, each in enumerate(resp, start=1):
            try:
                # Validate required fields
                if not isinstance(each, dict) or 'filename' not in each or 'size' not in each or 'direct_link' not in each or 'thumbnail' not in each:
                    logger.error(f"Missing required fields in Terabox response: {each}")
                    continue

                x = await is_valid_to_dl(_, user_id)
                if not x[0]:
                    return await status_msg.edit(x[1], reply_markup=x[2])
                    
                caption = f"Name: {each['filename']}\nSize: {format_size(each['size'])}\n\nPowered by @{UPDATE}"
                
                await status_msg.edit(
                    f"**Downloading Video {c} out of {len(resp)}...**\n\n{caption}",
                    reply_markup=markup,
                )

                filename = each['filename']
                task = asyncio.create_task(download_with_progress(
                    each['direct_link'], 
                    user_id, 
                    status_msg, 
                    filename, 
                    username
                ))
                downloads_manager[user_id] = {
                    'task': task,
                    'size': each['size'],
                    'downloaded': 0,
                    'method': 'd',
                    'last_update_time': time.time(),
                    'last_downloaded': 0
                }
                try:
                    path = await task
                except Exception as e:
                    if user_id in downloads_manager:
                        del downloads_manager[user_id]
                    return await status_msg.edit(f'Error while downloading: {e}')

                await status_msg.edit(
                    f"**Processing Video {c} out of {len(resp)}...**\n\n{caption}"
                )
                
                # Extract video info
                video_info = await asyncio.get_event_loop().run_in_executor(
                    PROCESS_POOL, 
                    extract_video_info, 
                    path
                )
                
                thumb = await download_thumb(each["thumbnail"], user_id)
                
                # Reset progress tracking for upload
                downloads_manager[user_id] = {
                    'downloaded': 0,
                    'size': each['size'],
                    'method': 'u',
                    'last_update_time': time.time(),
                    'last_downloaded': 0
                }
                
                try:
                    sent = await m.reply_video(
                        path,
                        duration=video_info['duration'],
                        width=video_info['width'],
                        height=video_info['height'],
                        caption=caption,
                        thumb=thumb,
                        progress=progress_callback,
                        progress_args=(user_id, status_msg, filename, username, "Uploading")
                    )
                    
                    # Send deletion warning as a reply (this will remain in chat)
                    warning_msg = await sent.reply(
                        "⚠️ **Note:**\nThe above video message will be automatically deleted from your chat after 10 minutes.\nPlease save or forward it to your saved messages if you want to keep it!",
                        quote=True
                    )
                    
                    if not await is_ad_disabled():
                        # Schedule message deletion without using mids.py
                        asyncio.create_task(delete_message_after(app, user_id, sent.id, 600))
                except Exception as e:
                    del downloads_manager[user_id]
                    return await status_msg.edit(f"Error while uploading: {str(e)}")
                
                copy = await sent.copy(VIDEO_STORE_GROUP_ID)
                ids.append(copy.id)
                await incr_usage(user_id)
                del downloads_manager[user_id]
            except Exception as e:
                logger.error(f"Error processing file {c}: {e}")
                continue
                
        if ids:  # Only store if some files were processed successfully
            try:
                await store_file(surl, VIDEO_STORE_GROUP_ID, ids)
            except Exception as e:
                logger.error(f"Error storing file mapping: {e}")
                
        if status_msg:
            await status_msg.delete()
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        if status_msg:
            await status_msg.edit_text(f"Download failed: {str(e)}")
    finally:
        # Cleanup if something was left in downloads_manager
        if user_id in downloads_manager:
            del downloads_manager[user_id]

async def delete_message_after(client: Client, chat_id: int, message_id: int, delay: int):
    """Delete a message after specified delay in seconds"""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

def progress_callback(current, total, user_id, message, filename, username, status="Downloading"):
    """Generic progress callback for both download and upload"""
    try:
        if user_id in downloads_manager:
            downloads_manager[user_id]['downloaded'] = current
            downloads_manager[user_id]['size'] = total
            
            # Calculate speed
            now = time.time()
            if 'last_update_time' not in downloads_manager[user_id]:
                downloads_manager[user_id]['last_update_time'] = now
                downloads_manager[user_id]['last_downloaded'] = current
                speed = 0
            else:
                time_diff = now - downloads_manager[user_id]['last_update_time']
                if time_diff >= UPDATE_INTERVAL:
                    speed = (current - downloads_manager[user_id]['last_downloaded']) / time_diff
                    downloads_manager[user_id]['last_update_time'] = now
                    downloads_manager[user_id]['last_downloaded'] = current
                    
                    # Update progress message
                    asyncio.create_task(update_progress_message(
                        message,
                        filename,
                        current,
                        total,
                        user_id,
                        username,
                        speed,
                        status
                    ))
    except Exception as e:
        logger.error(f"Error in progress callback: {e}")

# Use the same callback for both download and upload
download_callback = upload_callback = progress_callback

@Client.on_callback_query(filters.regex('^cancel$'))
async def cancel_cbq(_, q):
    user_id = q.from_user.id
    await q.answer()
    if user_id not in downloads_manager:
        return await q.answer('No Ongoing Process.', show_alert=True)
    downloads_manager[user_id]['task'].cancel()
    del downloads_manager[user_id]
    await q.message.delete()

@Client.on_callback_query(filters.regex("^try_again$"))
async def try_again_callback(client, callback_query):
    user_id = callback_query.from_user.id
    try:
        if (await client.get_chat_member(FSUB_ID, user_id)).status.name in ["MEMBER", "ADMINISTRATOR", "OWNER"]:
            await callback_query.message.delete()
            mention = f"[{callback_query.from_user.first_name}](tg://user?id={user_id})"
            await callback_query.message.reply(f"✅ Thank you for joining {mention}!\nYou can now use the bot.")
        else:
            await callback_query.answer("❌ You haven't joined the channel yet! Please join and try again.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in try_again callback: {e}")
        await callback_query.answer("❌ Something went wrong! Please try again later.", show_alert=True)

async def cleanup_dl_folder():
    """Clean up the DL folder once every 24 hours, skipping files that are being used"""
    while True:
        try:
            # Run cleanup every 24 hours
            await asyncio.sleep(86400)
            
            # Get list of files currently in use
            active_files = set()
            for user_id in downloads_manager:
                active_files.add(f'DL/{user_id}.mp4')
                active_files.add(f'DL/{user_id}.jpg')
            
            # Delete files that aren't being used
            files = glob.glob('DL/*.mp4') + glob.glob('DL/*.jpg')
            for file in files:
                if file not in active_files:
                    try:
                        os.remove(file)
                    except Exception as e:
                        print(f"Error deleting file {file}: {str(e)}")
        except Exception as e:
            print(f"DL folder cleanup error: {str(e)}")

async def clear_memory():
    """Force garbage collection to free up memory"""
    while True:
        await asyncio.sleep(300)
        gc.collect()

# Initialize process pool and start background tasks
def init_app():
    # Ensure DL directory exists with proper permissions
    os.makedirs('DL', exist_ok=True)
    os.chmod('DL', 0o755)
    
    # Start background tasks
    asyncio.create_task(cleanup_dl_folder())
    asyncio.create_task(clear_memory())

init_app()

@Client.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(_, message):
    try:
        msg = await message.reply_text("<b><blockquote>Processes are stopping. Bot is restarting...</blockquote></b>")
        await asyncio.sleep(3)
        await msg.edit("<b><blockquote>✅️ Bot has been restarted successfully!</blockquote></b>")
    except Exception as e:
        print(f"Error editing message: {e}")
        pass
    finally:
        os.execl(sys.executable, sys.executable, *sys.argv)

def upload_callback(current, total, user_id, message, filename, username):
    try:
        if user_id in downloads_manager:
            downloads_manager[user_id]['downloaded'] = current
            downloads_manager[user_id]['size'] = total
            
            # Calculate speed
            now = time.time()
            if 'last_update_time' not in downloads_manager[user_id]:
                downloads_manager[user_id]['last_update_time'] = now
                downloads_manager[user_id]['last_downloaded'] = current
                speed = 0
            else:
                time_diff = now - downloads_manager[user_id]['last_update_time']
                if time_diff >= UPDATE_INTERVAL:
                    speed = (current - downloads_manager[user_id]['last_downloaded']) / time_diff
                    downloads_manager[user_id]['last_update_time'] = now
                    downloads_manager[user_id]['last_downloaded'] = current
                    
                    # Update progress message
                    asyncio.create_task(update_progress_message(
                        message,
                        filename,
                        current,
                        total,
                        user_id,
                        username,
                        speed,
                        "Uploading"
                    ))
    except Exception as e:
        print(f"Error in upload callback: {e}")
