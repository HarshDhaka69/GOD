import os
import shutil

from alphagram import Client, idle
from config import *
import time

StartTime = time.time()

app = Client(
    'app',
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root='Plugins')
)

def run():
    app.start()
    shutil.rmtree('DL', ignore_errors=True)
    os.makedirs('DL', exist_ok=True)
    print('Bot Started.')
    idle()
