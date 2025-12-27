#!/usr/bin/env python3
"""
Telethon userbot: download media from a channel/group message and send it to you.
Usage (in any chat with your userbot account):
/download <target> <message_id>
target can be:
 - @username
 - -1001234567890  (numeric chat id)
 - a t.me link like https://t.me/c/3234242982/20  (the code will try to parse)
"""
import os
import re
import asyncio
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.types import PeerChannel
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
# You can either provide a saved session string or a filename for file-session
SESSION = os.getenv("SESSION", "userbot.session")
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "downloads")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

client = TelegramClient(SESSION, API_ID, API_HASH)


def parse_tme_link(link: str):
    """
    Try to parse t.me links of the form:
    - https://t.me/c/<chat_id>/<msg_id>
    - https://t.me/<username>/<msg_id>
    Return tuple (target, msg_id) or (None, None)
    """
    m = re.search(r"(?:https?://)?t\.me/(?:c/)?([^/\s]+)/?(\d+)?", link)
    if not m:
        return None, None
    part = m.group(1)
    msg_id = m.group(2)
    return part, int(msg_id) if msg_id else None


async def resolve_entity(target):
    """
    Try multiple ways to resolve an entity:
    - direct get_entity(target)
    - if numeric: try int(target) and -100... variants
    - for t.me/c numeric IDs, try both id and -100id
    """
    # direct attempt
    try:
        ent = await client.get_entity(target)
        return ent
    except Exception:
        pass

    # If target is numeric
    try:
        nid = int(target)
        # try as-is
        try:
            ent = await client.get_entity(nid)
            return ent
        except Exception:
            pass
        # try with -100 prefix if not present
        if nid > 0:
            try:
                ent = await client.get_entity(-1000000000000 + nid)
                return ent
            except Exception:
                pass
            try:
                ent = await client.get_entity(-100 * (10 ** 9) + nid)
                return ent
            except Exception:
                pass
        # try -100{nid}
        try:
            ent = await client.get_entity(-1000000000000 + nid)
            return ent
        except Exception:
            pass
    except Exception:
        pass

    # last resort: try as peer channel by id (if numeric string)
    try:
        if target.isdigit():
            cid = int(target)
            peer = PeerChannel(cid)
            return peer
    except Exception:
        pass

    return None


@client.on(events.NewMessage(pattern=r'^/download(?:\s+(.+))?'))
async def handler(event):
    """
    Handler for /download command.
    Accepts:
      /download <target> <message_id>
      target can be a t.me link, @username or numeric chat id
    """
    text = event.raw_text
    parts = text.split()
    if len(parts) < 3:
        await event.reply("Usage: /download <target> <message_id>\nExamples:\n/download @channelname 23\n/download -1001234567890 23\n/download https://t.me/c/3234242982 20")
        return

    target_raw = parts[1].strip()
    msg_id = parts[2].strip()

    # If target is a full t.me link with message id in link, parse it
    tpart, tmsg = parse_tme_link(target_raw)
    if tpart and tmsg:
        # user passed link with msg id in it; override msg_id
        target_raw = tpart
        msg_id = tmsg

    # Try to parse msg_id as int
    try:
        msg_id = int(msg_id)
    except Exception:
        await event.reply("Invalid message id. It must be an integer.")
        return

    status = await event.reply("Resolving target...")

    # Resolve entity
    entity = None
    try:
        entity = await resolve_entity(target_raw)
    except Exception as e:
        await status.edit(f"Failed to resolve entity: {e}")
        return

    if not entity:
        await status.edit("Could not resolve the target. Try @username or numeric chat id (-100...).")
        return

    await status.edit("Fetching message...")
    try:
        msg = await client.get_messages(entity, ids=msg_id)
    except RPCError as e:
        await status.edit(f"RPC error while fetching message: {e}")
        return
    except Exception as e:
        await status.edit(f"Error while fetching message: {e}")
        return

    if not msg:
        await status.edit("Message not found.")
        return

    if not msg.media:
        await status.edit("Message has no media to download.")
        return

    # prepare friendly filename
    friendly = f"{entity}_{msg_id}"
    outpath = os.path.join(DOWNLOAD_FOLDER, friendly)

    # progress updater
    last_update = 0

    def progress_callback(received, total):
        nonlocal last_update
        try:
            pct = int(received * 100 / total) if total else 0
            # limit edit frequency
            if pct != last_update and (pct % 5 == 0 or pct - last_update >= 3):
                # schedule an edit in the event loop
                asyncio.get_event_loop().create_task(status.edit(f"Downloading... {pct}% ({received}/{total})"))
                last_update = pct
        except Exception:
            pass

    await status.edit("Starting download...")
    try:
        file_path = await msg.download_media(file=outpath, progress_callback=progress_callback)
    except Exception as e:
        await status.edit(f"Download failed: {e}")
        return

    if not file_path:
        await status.edit("Failed to download (no path returned).")
        return

    await status.edit(f"Downloaded to server: {file_path}\nUploading to you...")

    # send file back to the same chat (you can modify to send to another chat id)
    try:
        await client.send_file(event.chat_id, file_path, caption=f"Downloaded from {target_raw} message {msg_id}")
        await status.edit("Upload complete.")
    except Exception as e:
        await status.edit(f"Upload failed: {e}")

    # Optionally remove the file to save disk
    try:
        os.remove(file_path)
    except Exception:
        pass


if __name__ == "__main__":
    print("Starting userbot...")
    client.start()
    print("Userbot started. Listening for /download commands.")
    client.run_until_disconnected()
