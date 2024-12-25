from telethon import TelegramClient, events
import os
import asyncio
import json
import random
from datetime import datetime

# API credentials
api_id = '20198581'
api_hash = '1697dbe0d74bd752b2d40134fdff9360'

# Initialize the Telegram Client
client = TelegramClient('userbot', api_id, api_hash, connection_retries=5)

device_owner_id = None
blacklisted_groups = []

# Auto-broadcast variables
auto_cast_running = False
auto_cast_min_delay = 60
auto_cast_max_delay = 120
auto_cast_message = ""

# AFK variables
afk_mode = False
afk_message = "⚠️ I'm currently AFK. I will respond when I'm back."
responded_users = set()

# Blacklist file
BLACKLIST_FILE = "blacklist.json"

# Load blacklist from file
def load_blacklist():
    global blacklisted_groups
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, 'r') as file:
                blacklisted_groups = json.load(file)
        except json.JSONDecodeError:
            print("⚠️ Blacklist file is corrupted. Resetting blacklist.")
            blacklisted_groups = []
    else:
        blacklisted_groups = []

def save_blacklist():
    with open(BLACKLIST_FILE, 'w') as file:
        json.dump(blacklisted_groups, file)

# Ensure blacklist is loaded
load_blacklist()

async def main():
    global device_owner_id

    await client.start()

    if not await client.is_user_authorized():
        print("❌ Client is not authorized. Please log in manually.")
        return

    device_owner = await client.get_me()
    device_owner_id = device_owner.id
    print(f"✅ Bot started as {device_owner.first_name} ({device_owner_id}).")

def is_device_owner(sender_id):
    return sender_id == device_owner_id

@client.on(events.NewMessage(pattern='/agc', outgoing=True))
async def start_autogcast(event):
    global auto_cast_running, auto_cast_min_delay, auto_cast_max_delay, auto_cast_message

    sender = await event.get_sender()
    if not is_device_owner(sender.id):
        await event.respond("❌ You are not authorized to use this command.")
        return

    if auto_cast_running:
        await event.respond("❌ Autogcast is already running.")
        return

    command_params = event.message.text.split(' ', 3)
    if len(command_params) < 4:
        await event.respond("❌ Incorrect command usage. Format: /agc <min_delay> <max_delay> <message>")
        return

    try:
        auto_cast_min_delay = int(command_params[1])
        auto_cast_max_delay = int(command_params[2])
        if auto_cast_min_delay > auto_cast_max_delay:
            raise ValueError("Minimum delay cannot be greater than maximum delay.")
    except ValueError as e:
        await event.respond(f"❌ Invalid input: {e}")
        return

    auto_cast_message = command_params[3]
    auto_cast_running = True
    await event.respond(f"✅ Autogcast started with a random delay between {auto_cast_min_delay} and {auto_cast_max_delay} seconds. Message: {auto_cast_message}")
    await run_autogcast()

async def run_autogcast():
    global auto_cast_running, auto_cast_message, auto_cast_min_delay, auto_cast_max_delay

    while auto_cast_running:
        try:
            dialogs = await client.get_dialogs()
            groups = [dialog for dialog in dialogs if dialog.is_group]

            for group in groups:
                if group.id in blacklisted_groups:
                    continue  # Skip blacklisted groups

                try:
                    await client.send_message(group.id, auto_cast_message)
                except Exception as e:
                    print(f"⚠️ Error sending message to group {group.title} ({group.id}): {e}")
                    continue

            delay = random.randint(auto_cast_min_delay, auto_cast_max_delay)
            print(f"⏳ Waiting for {delay} seconds before the next cycle...")
            await asyncio.sleep(delay)

        except Exception as e:
            print(f"⚠️ Error in autogcast loop: {e}")
            print("🔄 Retrying in 10 seconds...")
            await asyncio.sleep(10)

@client.on(events.NewMessage(pattern='/stopagc', outgoing=True))
async def stop_autogcast(event):
    global auto_cast_running

    sender = await event.get_sender()
    if not is_device_owner(sender.id):
        await event.respond("❌ You are not authorized to use this command.")
        return

    if not auto_cast_running:
        await event.respond("❌ No autogcast is running.")
        return

    auto_cast_running = False
    await event.respond("✅ Autogcast stopped.")

@client.on(events.NewMessage(pattern='/afk', outgoing=True))
async def enable_afk(event):
    global afk_mode, afk_message, responded_users

    sender = await event.get_sender()
    if not is_device_owner(sender.id):
        await event.respond("❌ You are not authorized to use this command.")
        return

    command_params = event.message.text.split(' ', 1)
    if len(command_params) > 1:
        afk_message = command_params[1]

    afk_mode = True
    responded_users.clear()  # Reset user responses
    await event.respond(f"✅ AFK mode enabled. Message: {afk_message}")

@client.on(events.NewMessage(pattern='/back', outgoing=True))
async def disable_afk(event):
    global afk_mode, responded_users

    sender = await event.get_sender()
    if not is_device_owner(sender.id):
        await event.respond("❌ You are not authorized to use this command.")
        return

    if not afk_mode:
        await event.respond("❌ You are not in AFK mode.")
        return

    afk_mode = False
    responded_users.clear()
    await event.respond("✅ AFK mode disabled.")

@client.on(events.NewMessage(incoming=True))
async def respond_afk(event):
    global afk_mode, responded_users

    if not afk_mode or not event.is_private:
        return

    sender = await event.get_sender()
    if sender.bot or sender.id in responded_users:
        return

    try:
        await event.respond(afk_message)
        responded_users.add(sender.id)
    except Exception as e:
        print(f"Error responding AFK: {e}")

async def run_bot():
    while True:
        try:
            await main()
            await client.run_until_disconnected()
        except Exception as e:
            print(f"⚠️ Bot disconnected: {e}")
            print("🔄 Retrying in 10 seconds...")
            await asyncio.sleep(10)

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("❌ Bot stopped by user.")
    finally:
        save_blacklist()
