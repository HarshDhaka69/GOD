#!/usr/bin/env python3
from telethon import TelegramClient, events
from telethon.tl.types import InputMessagesFilterPhotos, InputMessagesFilterVideo, InputMessagesFilterDocument, InputMessagesFilterGif
import asyncio
import logging
import sys
import time
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Your API credentials
API_ID = 20013090  # Replace with your API ID from https://my.telegram.org/apps
API_HASH = "f0b75eb977e4a1b3cb4a6ef48444806d"  # Replace with your API hash from https://my.telegram.org/apps

# Chat IDs
SOURCE_CHAT_ID = -1002677184960  # Source chat
TARGET_CHAT_ID = -1002333203264  # Target chat

# Session name (saved credentials)
SESSION_NAME = "user_session"

# Forwarding configuration
FORWARD_WITHOUT_CAPTION = True  # Set to True to remove captions
USE_CUSTOM_CAPTION = True  # Set to True to use custom caption
CUSTOM_CAPTION = "This File Is Uploaded By @TeraDelta"  # Custom caption text
START_MESSAGE_ID = 16  # Start forwarding from this message ID
MESSAGE_COUNT = 15000  # Number of messages to forward

# Rate limiting to avoid Telegram limits
DELAY_BETWEEN_MESSAGES = 1  # seconds

# Create the client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def forward_messages_without_caption():
    """Forward messages from source to target chat without captions"""
    print(f"Starting to forward messages from message ID {START_MESSAGE_ID}")
    
    # Try to get information about source chat
    try:
        source_entity = await client.get_entity(SOURCE_CHAT_ID)
        print(f"Successfully connected to source chat: {source_entity.title if hasattr(source_entity, 'title') else source_entity.id}")
    except Exception as e:
        print(f"Error connecting to source chat: {e}")
        return
        
    # Try to get information about target chat
    try:
        target_entity = await client.get_entity(TARGET_CHAT_ID)
        print(f"Successfully connected to target chat: {target_entity.title if hasattr(target_entity, 'title') else target_entity.id}")
    except Exception as e:
        print(f"Error connecting to target chat: {e}")
        return
    
    success_count = 0
    failure_count = 0
    
    # Calculate the end message ID
    end_message_id = START_MESSAGE_ID + MESSAGE_COUNT
    
    for msg_id in range(START_MESSAGE_ID, end_message_id):
        path = None
        try:
            # Get the message from source chat
            message = await client.get_messages(SOURCE_CHAT_ID, ids=msg_id)
            
            if not message:
                print(f"Message ID {msg_id} not found in source chat")
                failure_count += 1
                continue
                
            print(f"Processing message ID {msg_id}")
            
            if message.media:
                # Download media locally first
                path = await message.download_media(file="temp_media/")
                
                # Send media with custom caption or no caption
                caption = CUSTOM_CAPTION if USE_CUSTOM_CAPTION else ""
                
                # Preserve media attributes
                if message.photo:
                    # For photos, pass the attributes
                    if hasattr(message.photo, 'sizes'):
                        # Find the largest size
                        largest_size = max(message.photo.sizes, key=lambda s: getattr(s, 'w', 0) * getattr(s, 'h', 0))
                        width = getattr(largest_size, 'w', None)
                        height = getattr(largest_size, 'h', None)
                        await client.send_file(
                            TARGET_CHAT_ID, 
                            path, 
                            caption=caption,
                            attributes=message.media.photo.attributes if hasattr(message.media.photo, 'attributes') else None,
                            width=width,
                            height=height
                        )
                    else:
                        await client.send_file(TARGET_CHAT_ID, path, caption=caption)
                elif message.video:
                    # For videos, pass all the relevant attributes
                    video_attributes = []
                    width = None
                    height = None
                    duration = None
                    
                    # Extract video attributes
                    if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
                        for attr in message.media.document.attributes:
                            if hasattr(attr, 'w'):
                                width = attr.w
                            if hasattr(attr, 'h'):
                                height = attr.h
                            if hasattr(attr, 'duration'):
                                duration = attr.duration
                            # Add all original attributes to preserve them
                            video_attributes.append(attr)
                    
                    await client.send_file(
                        TARGET_CHAT_ID, 
                        path, 
                        caption=caption,
                        attributes=video_attributes,
                        width=width,
                        height=height,
                        duration=duration,
                        supports_streaming=True
                    )
                elif message.document or message.gif:
                    # For documents/GIFs, preserve attributes
                    doc_attributes = []
                    if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
                        doc_attributes = message.media.document.attributes
                    
                    await client.send_file(
                        TARGET_CHAT_ID, 
                        path, 
                        caption=caption,
                        attributes=doc_attributes
                    )
                else:
                    # For other media types
                    await client.send_file(TARGET_CHAT_ID, path, caption=caption)
            else:
                # For text messages, send a new message instead of forwarding
                if message.text:
                    await client.send_message(TARGET_CHAT_ID, message.text)
                else:
                    # If it's neither media nor text, just skip
                    print(f"Skipping message {msg_id} - not media or text")
                
            success_count += 1
            print(f"Successfully processed message {msg_id} ({success_count} total)")
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
            
        except Exception as e:
            print(f"Error forwarding message ID {msg_id}: {e}")
            failure_count += 1
            
            # Add a longer delay if we hit an error
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES * 2)
        finally:
            # Always clean up downloaded files, even if an error occurred
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Cleaned up temporary file: {path}")
                except Exception as e:
                    print(f"Failed to delete temporary file {path}: {e}")
    
    # Clean up any remaining files in temp_media directory
    cleanup_temp_directory()
    print(f"Forwarding completed. Successfully forwarded {success_count} messages. Failed: {failure_count}")

async def forward_all_messages():
    """Forward all messages from source chat to target chat"""
    print("Starting to forward all messages from the source chat")
    
    # Try to get information about source chat
    try:
        source_entity = await client.get_entity(SOURCE_CHAT_ID)
        print(f"Successfully connected to source chat: {source_entity.title if hasattr(source_entity, 'title') else source_entity.id}")
    except Exception as e:
        print(f"Error connecting to source chat: {e}")
        return
        
    # Try to get information about target chat
    try:
        target_entity = await client.get_entity(TARGET_CHAT_ID)
        print(f"Successfully connected to target chat: {target_entity.title if hasattr(target_entity, 'title') else target_entity.id}")
    except Exception as e:
        print(f"Error connecting to target chat: {e}")
        return
    
    success_count = 0
    failure_count = 0
    
    # Get all messages from the chat (this will retrieve them in chunks)
    # The newest messages come first, so we'll reverse them
    messages = []
    
    print("Retrieving all messages, this might take some time...")
    async for message in client.iter_messages(SOURCE_CHAT_ID):
        messages.append(message)
        if len(messages) % 100 == 0:
            print(f"Retrieved {len(messages)} messages so far...")
    
    print(f"Retrieved a total of {len(messages)} messages")
    # Reverse messages to process from oldest to newest
    messages.reverse()
    
    for index, message in enumerate(messages):
        path = None
        try:
            print(f"Processing message {index+1}/{len(messages)} (ID: {message.id})")
            
            if message.media:
                # Download media locally first
                path = await message.download_media(file="temp_media/")
                
                # Send media with custom caption or no caption
                caption = CUSTOM_CAPTION if USE_CUSTOM_CAPTION else ""
                
                # Preserve media attributes
                if message.photo:
                    # For photos, pass the attributes
                    if hasattr(message.photo, 'sizes'):
                        # Find the largest size
                        largest_size = max(message.photo.sizes, key=lambda s: getattr(s, 'w', 0) * getattr(s, 'h', 0))
                        width = getattr(largest_size, 'w', None)
                        height = getattr(largest_size, 'h', None)
                        await client.send_file(
                            TARGET_CHAT_ID, 
                            path, 
                            caption=caption,
                            attributes=message.media.photo.attributes if hasattr(message.media.photo, 'attributes') else None,
                            width=width,
                            height=height
                        )
                    else:
                        await client.send_file(TARGET_CHAT_ID, path, caption=caption)
                elif message.video:
                    # For videos, pass all the relevant attributes
                    video_attributes = []
                    width = None
                    height = None
                    duration = None
                    
                    # Extract video attributes
                    if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
                        for attr in message.media.document.attributes:
                            if hasattr(attr, 'w'):
                                width = attr.w
                            if hasattr(attr, 'h'):
                                height = attr.h
                            if hasattr(attr, 'duration'):
                                duration = attr.duration
                            # Add all original attributes to preserve them
                            video_attributes.append(attr)
                    
                    await client.send_file(
                        TARGET_CHAT_ID, 
                        path, 
                        caption=caption,
                        attributes=video_attributes,
                        width=width,
                        height=height,
                        duration=duration,
                        supports_streaming=True
                    )
                elif message.document or message.gif:
                    # For documents/GIFs, preserve attributes
                    doc_attributes = []
                    if hasattr(message.media, 'document') and hasattr(message.media.document, 'attributes'):
                        doc_attributes = message.media.document.attributes
                    
                    await client.send_file(
                        TARGET_CHAT_ID, 
                        path, 
                        caption=caption,
                        attributes=doc_attributes
                    )
                else:
                    # For other media types
                    await client.send_file(TARGET_CHAT_ID, path, caption=caption)
            else:
                # For text messages, send a new message instead of forwarding
                if message.text:
                    await client.send_message(TARGET_CHAT_ID, message.text)
                else:
                    # If it's neither media nor text, just skip
                    print(f"Skipping message {index+1} - not media or text")
                
            success_count += 1
            if success_count % 10 == 0:
                print(f"Successfully processed {success_count} messages so far")
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
            
        except Exception as e:
            print(f"Error forwarding message ID {message.id}: {e}")
            failure_count += 1
            
            # Add a longer delay if we hit an error
            await asyncio.sleep(DELAY_BETWEEN_MESSAGES * 2)
        finally:
            # Always clean up downloaded files, even if an error occurred
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"Cleaned up temporary file: {path}")
                except Exception as e:
                    print(f"Failed to delete temporary file {path}: {e}")
    
    # Clean up any remaining files in temp_media directory
    cleanup_temp_directory()
    print(f"Forwarding completed. Successfully forwarded {success_count} messages. Failed: {failure_count}")

def cleanup_temp_directory():
    """Clean up any files left in the temporary directory"""
    temp_dir = "temp_media"
    try:
        file_count = 0
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    file_count += 1
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        
        if file_count > 0:
            print(f"Cleaned up {file_count} remaining files in {temp_dir} directory")
    except Exception as e:
        print(f"Error cleaning up temporary directory: {e}")

async def interactive_forward():
    """Interactive menu for forwarding messages"""
    global START_MESSAGE_ID, MESSAGE_COUNT, FORWARD_WITHOUT_CAPTION, USE_CUSTOM_CAPTION, CUSTOM_CAPTION
    
    print("\n=== Telegram User Account Forwarder ===")
    print(f"Source Chat ID: {SOURCE_CHAT_ID}")
    print(f"Target Chat ID: {TARGET_CHAT_ID}")
    
    while True:
        print("\nOptions:")
        print("1. Start forwarding messages from specific ID")
        print("2. Forward ALL messages from source chat")
        print("3. Change starting message ID (current: {})".format(START_MESSAGE_ID))
        print("4. Change message count (current: {})".format(MESSAGE_COUNT))
        print("5. Toggle caption removal (current: {})".format("Removing captions" if FORWARD_WITHOUT_CAPTION else "Keeping captions"))
        print("6. Toggle custom caption (current: {})".format("Using custom caption" if USE_CUSTOM_CAPTION else "Not using custom caption"))
        print("7. Change custom caption (current: {})".format(CUSTOM_CAPTION))
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ")
        
        if choice == "1":
            await forward_messages_without_caption()
        elif choice == "2":
            confirm = input("WARNING: This will forward ALL messages from the source chat. Continue? (y/n): ")
            if confirm.lower() == 'y':
                await forward_all_messages()
            else:
                print("Operation cancelled.")
        elif choice == "3":
            try:
                START_MESSAGE_ID = int(input("Enter new starting message ID: "))
            except ValueError:
                print("Please enter a valid number")
        elif choice == "4":
            try:
                MESSAGE_COUNT = int(input("Enter new message count: "))
            except ValueError:
                print("Please enter a valid number")
        elif choice == "5":
            FORWARD_WITHOUT_CAPTION = not FORWARD_WITHOUT_CAPTION
            print(f"Caption removal set to: {FORWARD_WITHOUT_CAPTION}")
        elif choice == "6":
            USE_CUSTOM_CAPTION = not USE_CUSTOM_CAPTION
            print(f"Custom caption set to: {USE_CUSTOM_CAPTION}")
        elif choice == "7":
            CUSTOM_CAPTION = input("Enter new custom caption: ")
            print(f"Custom caption updated to: {CUSTOM_CAPTION}")
        elif choice == "8":
            print("Exiting...")
            break
        else:
            print("Invalid choice, please try again.")

async def main():
    # Ensure temp directory exists
    os.makedirs("temp_media", exist_ok=True)
    
    # Start interactive menu
    await interactive_forward()
    
    # Clean up temp directory when finished
    cleanup_temp_directory()

# Start the client
with client:
    client.loop.run_until_complete(main()) 
