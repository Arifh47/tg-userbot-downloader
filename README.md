# Telethon Userbot — Download protected/private media from channels you have access to

WARNING: Only use this for content you are authorized to access. Do NOT use to bypass other people's privacy or to distribute copyrighted content without permission.

## What this does
- Runs as a "user" (your account) using Telethon.
- Accepts `/download <target> <message_id>` commands and downloads the referenced media from the target chat/channel message, then uploads it to the chat where you issued the command.

## Files
- `bot.py` — main userbot script.
- `session_string.py` — create a session string interactively.
- `requirements.txt` — Python dependencies.
- `.env.example` — environment variables example.

## Setup
1. Create a Telegram application to get `api_id` and `api_hash`:
   - Visit https://my.telegram.org/apps and create a new app (if you don't have one).
   - Copy `api_id` and `api_hash`.

2. Prepare environment:
   - Copy `.env.example` to `.env` and fill `API_ID` and `API_HASH`.
   - Optionally set `SESSION` to a filename (e.g. `userbot.session`) or leave default.

3. Install dependencies:
   - python3 -m venv venv
   - source venv/bin/activate
   - pip install -r requirements.txt

4. Create a session string (recommended, so you can reuse session safely):
   - python3 session_string.py
   - Follow login steps (phone -> code). Copy the printed session string and add it to `.env` as `SESSION=the_long_string_here`
     - Alternatively you can keep a file-based session; the script will create `userbot.session` file when you first run bot.py interactively.

5. Run the bot:
   - python3 bot.py
   - From the same Telegram account (or another chat with yourself), send:
     `/download @channelname 23`
     or
     `/download -1001234567890 23`
     or
     `/download https://t.me/c/3234242982 20`

## Deploy to VPS (quick)
- Use systemd or screen/tmux.
- Example systemd service (`/etc/systemd/system/userbot.service`):
  ```
  [Unit]
  Description=Telethon userbot
  After=network.target

  [Service]
  Type=simple
  User=youruser
  WorkingDirectory=/home/youruser/yourbotdir
  ExecStart=/home/youruser/yourbotdir/venv/bin/python /home/youruser/yourbotdir/bot.py
  Restart=on-failure
  EnvironmentFile=/home/youruser/yourbotdir/.env

  [Install]
  WantedBy=multi-user.target
  ```
- Reload daemon: `sudo systemctl daemon-reload`
- Start: `sudo systemctl start userbot`
- Enable on boot: `sudo systemctl enable userbot`
- Check logs: `sudo journalctl -u userbot -f`

## Notes & tips
- Keep your session string private. Anyone with it can control your account.
- For very large files consider downloading to a mounted disk with large capacity or uploading directly to cloud storage (S3) instead of re-uploading to Telegram.
- If a target is a private channel, you must be a member of that channel. The userbot runs as *your* user and will only be able to download content you are allowed to see.
- The script uses a basic resolver for links like `t.me/c/<id>/<msg_id>` but link parsing can be tricky for some chat ids; if resolution fails try using `@username` or the full numeric chat id (e.g. -1001234567890).

## Legal / Ethical
- Do not use to circumvent privacy or to steal content. Follow Telegram Terms of Service and local law.
- If you plan to store or redistribute content, ensure you have permission.

## Enhancements you may add
- A web UI to submit targets (but then server must protect session string).
- Send progress updates to a separate log chat.
- Add auto-cleanup, retry logic, rate-limit handling, and ability to upload to S3/Google Drive.
