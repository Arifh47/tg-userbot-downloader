#!/usr/bin/env python3
"""
Bridge: Aiogram bot accepts requests, Telethon user client fetches media.
Usage:
 - Configure .env (API_ID, API_HASH, SESSION, BOT_TOKEN, ALLOWED_USERS, MAX_CONCURRENT)
 - Run: python3 bridge.py
Commands (via Bot):
 - /download <target> <message_id>
 - /status  (admin only)
 - /allowme (optional flow to request being allowed)
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
SESSION = os.getenv("SESSION") or "userbot.session"
BOT_TOKEN = os.getenv("BOT_TOKEN") or ""
# comma separated Telegram user ids allowed; if empty and PUBLIC_MODE=1 then open to all
ALLOWED_USERS = [int(x) for x in (os.getenv("ALLOWED_USERS") or "").split(",") if x.strip().isdigit()]
PUBLIC_MODE = os.getenv("PUBLIC_MODE", "0") == "1"
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT") or 2)

if not (API_ID and API_HASH and BOT_TOKEN):
    raise SystemExit("Please set API_ID, API_HASH and BOT_TOKEN in .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from telethon import TelegramClient
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ParseMode

user_client = TelegramClient(SESSION, API_ID, API_HASH)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# simple semaphore to limit concurrency (prevent abuse)
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

def is_allowed(user_id: int) -> bool:
    if PUBLIC_MODE:
        return True
    return user_id in ALLOWED_USERS

@dp.message_handler(commands=['start', 'help'])
async def cmd_help(message: types.Message):
    await message.reply(
        "Send /download <target> <message_id>\nExamples:\n/download @channelname 23\n/download https://t.me/c/3234242982 20\n\nNote: Only content you are authorized to view can be fetched."
    )

@dp.message_handler(commands=['status'])
async def cmd_status(message: types.Message):
    if message.from_user and message.from_user.id in ALLOWED_USERS:
        await message.reply(f"Service running.\nAllowed users: {ALLOWED_USERS}\nPublic mode: {PUBLIC_MODE}\nMax concurrent: {MAX_CONCURRENT}")
    else:
        await message.reply("You are not authorized to check status.")

@dp.message_handler(commands=['download'])
async def cmd_download(message: types.Message):
    uid = message.from_user.id if message.from_user else None
    if not is_allowed(uid):
        await message.reply("You are not authorized to use this bot. Contact admin.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Usage: /download <target> <message_id>\nExample: /download @channelname 23")
        return

    target_raw = parts[1]
    try:
        msg_id = int(parts[2])
    except:
        await message.reply("Invalid message id (must be integer).")
        return

    # Acquire semaphore (rate-limit concurrent downloads)
    acquired = await semaphore.acquire()
    if not acquired:
        await message.reply("Server busy. Try again later.")
        return

    status_msg = await message.reply(f"Queued. Starting download for {target_raw} #{msg_id} ...")
    try:
        # resolve entity
        entity = await user_client.get_entity(target_raw)
        tele_msg = await user_client.get_messages(entity, ids=msg_id)
        if not tele_msg:
            await status_msg.edit("Message not found.")
            return
        if not tele_msg.media:
            await status_msg.edit("Message has no media to download.")
            return

        # download with progress callback (simple)
        outdir = "downloads"
        os.makedirs(outdir, exist_ok=True)

        last_pct = -1
        def progress_cb(received, total):
            nonlocal last_pct
            try:
                pct = int(received * 100 / total) if total else 0
                # update every 10%
                if pct - last_pct >= 10:
                    last_pct = pct
                    asyncio.get_event_loop().create_task(status_msg.edit(f"Downloading... {pct}%"))
            except Exception:
                pass

        await status_msg.edit("Downloading...")
        file_path = await tele_msg.download_media(file=outdir, progress_callback=progress_cb)
        if not file_path:
            await status_msg.edit("Download failed.")
            return

        await status_msg.edit("Uploading to Telegram (this bot)...")
        # send as document to the same chat
        await bot.send_document(chat_id=message.chat.id, document=open(file_path, "rb"),
                                caption=f"Downloaded from {target_raw} message {msg_id}")
        await status_msg.edit("Done. File sent.")
    except Exception as e:
        logger.exception("Error in download handler")
        await status_msg.edit(f"Error: {e}")
    finally:
        try:
            semaphore.release()
        except Exception:
            pass
        # cleanup local file(s) if exists
        try:
            if 'file_path' in locals() and file_path:
                os.remove(file_path)
        except Exception:
            pass

async def on_startup(dp):
    await user_client.start()
    logger.info("Telethon user client started")
    # optional: print user info
    try:
        me = await user_client.get_me()
        logger.info(f"User session logged in as: {me.username or me.first_name} ({me.id})")
    except Exception:
        pass

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
