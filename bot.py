import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import logging
import tweepy

logging.basicConfig(level=logging.INFO)

# Load environment variables directly from OS environment (no dotenv)
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID_PING = int(os.getenv("CHANNEL_ID_PING"))
CHANNEL_ID_NO_PING = int(os.getenv("CHANNEL_ID_NO_PING"))
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# Setup Twitter API client using tweepy OAuth1UserHandler
auth = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
)
twitter_api = tweepy.API(auth)

STREAMERS = {
    "jasontheween": {"last_title": None, "ping": True},
    "stableronaldo": {"last_title": None, "ping": False},
    "adapt": {"last_title": None, "ping": False},
    "plaqueboymax": {"last_title": None, "ping": False},
    "silky": {"last_title": None, "ping": False},
    "lacy": {"last_title": None, "ping": False}
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

access_token = None

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
            access_token = data.get("access_token")

async def get_stream_data(user_login):
    url = f"https://api.twitch.tv/helix/streams?user_login={user_login}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

async def get_user_info(user_login):
    url = f"https://api.twitch.tv/helix/users?login={user_login}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get("data"):
                return data["data"][0]
            return None

async def get_channel_info(user_login):
    user_info = await get_user_info(user_login)
    if not user_info:
        return None
    broadcaster_id = user_info["id"]
    url = f"https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster_id}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data.get("data"):
                return data["data"][0]
            return None

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await get_twitch_token()
    bot.loop.create_task(check_titles_loop())

async def check_titles_loop():
    await bot.wait_until_ready()
    channel_ping = bot.get_channel(CHANNEL_ID_PING)
    channel_no_ping = bot.get_channel(CHANNEL_ID_NO_PING)

    while not bot.is_closed():
        for streamer, data in STREAMERS.items():
            try:
                stream_data = await get_stream_data(streamer)
                channel_info = await get_channel_info(streamer)
                if not channel_info:
                    continue

                current_title = channel_info.get("title")
                is_live = bool(stream_data.get("data"))

                if current_title != data["last_title"]:
                    data["last_title"] = current_title

                    user_info = await get_user_info(streamer)
                    if not user_info:
                        continue

                    embed = discord.Embed(
                        title=user_info["display_name"],
                        description=current_title,
                        color=discord.Color.green() if is_live else discord.Color.greyple()
                    )
                    embed.set_thumbnail(url=user_info["profile_image_url"])
                    status_text = "🔴 LIVE" if is_live else "⚫ OFFLINE"
                    embed.set_footer(text=status_text)

                    if data["ping"]:
                        await channel_ping.send("@everyone", embed=embed)
                        if streamer == "jasontheween":
                            tweet_text = f"{status_text} JasonTheWeen has changed his title to → {current_title}"
                            twitter_api.update_status(tweet_text)
                    else:
                        await channel_no_ping.send(embed=embed)
            except Exception as e:
                print(f"Error for {streamer}: {e}")
        await asyncio.sleep(60)

bot.run(TOKEN)
