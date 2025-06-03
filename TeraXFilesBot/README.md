# Terabox Video Downloader Bot

A Telegram bot that downloads videos from Terabox links and sends them directly to Telegram. Built with performance and user experience in mind.

## Features

- 🚀 Fast downloads with optimized chunk sizes for NVMe SSDs
- 📊 Real-time progress tracking with fancy formatting
- 💾 Smart file caching system
- 👑 Premium user system with increased limits
- 🔄 Auto-deletion of messages after 10 minutes
- 📝 Detailed logging system
- ⚡ Concurrent download support
- 🎯 Force subscribe feature
- 💰 Built-in payment system with QR codes

## Setup

1. Clone this repository
2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure `config.py` with your values:
   - `API_ID` & `API_HASH`: Get from [my.telegram.org](https://my.telegram.org)
   - `BOT_TOKEN`: Get from [@BotFather](https://t.me/BotFather)
   - `MONGO_DB_URI`: Your MongoDB connection string
   - `OWNER_ID`: Your Telegram user ID
   - Other configuration values as needed

## Usage

1. Start the bot:
   ```bash
   python main.py
   ```

2. Send a Terabox link to the bot

## Commands

- `/start` - Start the bot
- `/plans` - View premium plans
- `/myplan` - Check your current plan
- `/verify` - Verify payment
- `/settings` - Admin settings (owner only)
- `/restart` - Restart bot (owner only)

## Premium Features

- 99 downloads per day (vs 10 for free users)
- No ads required
- Priority support

## Technical Details

- Uses chunked downloads (50MB chunks)
- Optimized buffer sizes (8MB)
- Connection pooling
- Concurrent download limit of 3
- Progress updates every 3 seconds
- Automatic cleanup of downloaded files after 24 hours

## Database Collections

- `premium_users`: Premium user management
- `usage`: Daily usage tracking
- `ads_shortner`: Ads/shortner settings
- `file_mapper`: File caching system

## Error Handling

- Comprehensive error logging
- Automatic cleanup of resources
- Graceful failure handling
- User-friendly error messages

## Contributing

Feel free to open issues and submit pull requests.

## License

This project is licensed under the MIT License.

## Credits

- Built with [Alphagram](https://docs.alphagram.app/)
- Powered by [TeraXHub](https://t.me/TeraXHub)