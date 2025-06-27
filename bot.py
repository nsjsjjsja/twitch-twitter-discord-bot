import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import os

# Enable all required intents
intents = discord.Intents.default()
intents.message_content = True  # Required to respond to commands

bot = commands.Bot(command_prefix='!', intents=intents)

# Load credentials from environment
TOKEN = os.environ["TOKEN"]
TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

access_token = None

# Structure: {username: {"channel": channel_id, "ping": True/False, "last_title": str}}
watched_streamers = {}

# Get Twitch access token
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

# Get Twitch profile image
async def get_profile(username):
    url = f"https://api.twitch.tv/helix/users?login={username}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data["data"]:
                return data["data"][0]["profile_image_url"]
            return None

# Get stream info (title)
async def get_stream(username):
    url = f"https://api.twitch.tv/helix/streams?user_login={username}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

# When bot starts
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await get_twitch_token()
    check_streams.start()

# !watchp command (with @everyone ping)
@bot.command()
async def watchp(ctx, username: str):
    username = username.lower()
    watched_streamers[username] = {
        "channel": ctx.channel.id,
        "ping": True,
        "last_title": None
    }
    await ctx.send(f"🔔 Now watching `{username}` with @everyone ping.")

# !watch command (no ping)
@bot.command()
async def watch(ctx, username: str):
    username = username.lower()
    watched_streamers[username] = {
        "channel": ctx.channel.id,
        "ping": False,
        "last_title": None
    }
    await ctx.send(f"👀 Now watching `{username}` silently (no ping).")

# !unwatch command
@bot.command()
async def unwatch(ctx, username: str):
    username = username.lower()
    if username in watched_streamers:
        del watched_streamers[username]
        await ctx.send(f"🗑️ Unwatched `{username}`.")
    else:
        await ctx.send(f"`{username}` was not being watched.")

# !clear command
@bot.command()
async def clear(ctx):
    watched_streamers.clear()
    await ctx.send("🧹 All streamers removed from watchlist.")

# Background task: checks every 60 seconds
@tasks.loop(seconds=60)
async def check_streams():
    for username, info in list(watched_streamers.items()):
        try:
            data = await get_stream(username)
            if data["data"]:
                new_title = data["data"][0]["title"]
                if info["last_title"] != new_title:
                    watched_streamers[username]["last_title"] = new_title
                    pfp = await get_profile(username)

                    embed = discord.Embed(
                        title=f"{username}'s stream title changed!",
                        description=f"> {new_title}",
                        color=discord.Color.purple()
                    )
                    if pfp:
                        embed.set_thumbnail(url=pfp)
                    embed.set_footer(text="Twitch Title Watcher Bot")

                    channel = bot.get_channel(info["channel"])
                    if channel:
                        await channel.send(
                            content="@everyone" if info["ping"] else None,
                            embed=embed
                        )
        except Exception as e:
            print(f"[Error for {username}] {e}")

# Start the bot
bot.run(TOKEN)