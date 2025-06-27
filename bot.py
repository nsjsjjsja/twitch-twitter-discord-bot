import os
import discord
import aiohttp
import asyncio
import tweepy
from discord import Embed

# Discord intents
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# Environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

CHANNEL_ID_PING = int(os.getenv("CHANNEL_ID_PING"))
CHANNEL_ID_NO_PING = int(os.getenv("CHANNEL_ID_NO_PING"))

# Tweepy OAuth1.0a Authentication for Twitter
twitter_auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET"),
)
twitter_api = tweepy.API(twitter_auth)

# List of streamers to monitor
# Format: (streamer_login, discord_channel_id, ping_role_bool)
STREAMERS = [
    ("jasontheween", CHANNEL_ID_PING, True),
    ("stableronaldo", CHANNEL_ID_NO_PING, False),
    ("adapt", CHANNEL_ID_NO_PING, False),
    ("plaqueboymax", CHANNEL_ID_NO_PING, False),
    ("silky", CHANNEL_ID_NO_PING, False),
    ("lacy", CHANNEL_ID_NO_PING, False),
]

last_title = {}

async def get_twitch_token():
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            return data["access_token"]

async def get_stream_data(streamer):
    url = f"https://api.twitch.tv/helix/streams?user_login={streamer}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

async def fetch_user_info(streamer):
    url = f"https://api.twitch.tv/helix/users?login={streamer}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            if data["data"]:
                return data["data"][0]
            return None

@bot.event
async def on_ready():
    global access_token
    print(f"Logged in as {bot.user}")
    access_token = await get_twitch_token()
    bot.loop.create_task(check_title_loop())

async def check_title_loop():
    global last_title
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            for streamer, channel_id, ping_role in STREAMERS:
                data = await get_stream_data(streamer)
                is_live = bool(data["data"])
                current_title = data["data"][0]["title"] if is_live else "Offline"

                if streamer not in last_title:
                    last_title[streamer] = None

                if current_title != last_title[streamer]:
                    last_title[streamer] = current_title
                    channel = bot.get_channel(channel_id)
                    user_info = await fetch_user_info(streamer)
                    profile_img = user_info["profile_image_url"] if user_info else None
                    display_name = user_info["display_name"] if user_info else streamer

                    embed = Embed(title=display_name, description=f"**{current_title}**", color=0x9146FF)
                    if profile_img:
                        embed.set_thumbnail(url=profile_img)

                    message_content = "@everyone" if ping_role else None

                    # Send Discord message with embed and optional ping
                    if message_content:
                        await channel.send(content=message_content, embed=embed)
                    else:
                        await channel.send(embed=embed)

                    # Twitter post only for jasontheween
                    if streamer == "jasontheween":
                        emoji = "🔴" if is_live else "⚫"
                        tweet_text = f"{emoji} JasonTheWeen has changed his title to -> {current_title}"
                        try:
                            twitter_api.update_status(tweet_text)
                            print(f"Tweeted: {tweet_text}")
                        except Exception as e:
                            print(f"Failed to tweet: {e}")

        except Exception as e:
            print(f"Error in check_title_loop: {e}")

        await asyncio.sleep(60)

bot.run(TOKEN)

