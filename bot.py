import discord
import aiohttp
import asyncio
import os
from flask import Flask
from threading import Thread

# Optional keep-alive server (can be removed for Render)
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    Thread(target=run).start()

# Environment Variables
TOKEN = os.environ["TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
TWITCH_USERNAME = "jasontheween"
TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

# Discord client
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# Globals
access_token = None
last_title = None
profile_image_url = None

# Twitch Token
async def get_twitch_token():
    global access_token
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            access_token = data["access_token"]

# Get Twitch user info for avatar
async def get_twitch_user_data():
    global profile_image_url
    url = f"https://api.twitch.tv/helix/users?login={TWITCH_USERNAME}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data["data"]:
                profile_image_url = data["data"][0]["profile_image_url"]

# Get current stream info
async def get_stream_data():
    url = f"https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await get_twitch_token()
    await get_twitch_user_data()
    bot.loop.create_task(check_title_loop())

# Loop to check stream title every 60 seconds
async def check_title_loop():
    global last_title
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while not bot.is_closed():
        try:
            data = await get_stream_data()
            if data["data"]:
                current_title = data["data"][0]["title"]
                if current_title != last_title:
                    last_title = current_title

                    embed = discord.Embed(
                        title="🔴 Stream Title Changed!",
                        description=f"**{TWITCH_USERNAME}**'s new stream title:\n> {current_title}",
                        color=discord.Color.purple()
                    )
                    embed.set_thumbnail(url=profile_image_url)
                    embed.set_footer(text="Twitch Title Watcher Bot")

                    await channel.send(content="@everyone", embed=embed)

        except Exception as e:
            print(f"[Error] {e}")

        await asyncio.sleep(60)

# Keep alive (only needed for Replit)
keep_alive()

# Start bot
bot.run(TOKEN)