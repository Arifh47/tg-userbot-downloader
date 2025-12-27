#!/usr/bin/env python3
"""
Run this once to create and print a session string.
Usage:
  1) Fill API_ID and API_HASH in the .env or export env vars.
  2) python3 session_string.py
  3) Follow the interactive login (phone + code) and copy the printed session string.
"""
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""

if not API_ID or not API_HASH:
    print("Please set API_ID and API_HASH in environment (.env) before running.")
    exit(1)

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("Login successful.")
    print("Session string (keep secret):")
    print(client.session.save())
