import discord
import aiohttp
import asyncio
import os

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID_PING = int(os.environ["CHANNEL_ID_PING"])      # For jasontheween (with ping)
CHANNEL_ID_NO_PING = int(os.environ["CHANNEL_ID_NO_PING"])  # For others (no ping)

STREAMERS = {
    "jasontheween": {"channel_id": CHANNEL_ID_PING, "ping": True},
    "stableronaldo": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "adapt": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "plaqueboymax": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "silky": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "lacy": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
}

TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

access_token = None
last_titles = {streamer: None for streamer in STREAMERS}

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

async def get_stream_data(username):
    url = f"https://api.twitch.tv/helix/streams?user_login={username}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.json()

async def get_user_data(username):
    # Gets user info including profile pic and "stream title" (description)
    url = f"https://api.twitch.tv/helix/channels?broadcaster_login={username}"
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

def make_embed(username, title, is_live, profile_image_url):
    color = discord.Color.red() if is_live else discord.Color.dark_grey()
    embed = discord.Embed(
        title=f"{username}",
        description=title,
        color=color
    )
    if profile_image_url:
        embed.set_thumbnail(url=profile_image_url)
    embed.set_footer(text="Live" if is_live else "Offline")
    return embed

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await get_twitch_token()
    bot.loop.create_task(check_title_loop())

async def check_title_loop():
    global last_titles
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            for streamer, info in STREAMERS.items():
                data = await get_stream_data(streamer)
                user_data = await get_user_data(streamer)
                profile_image_url = user_data["thumbnail_url"].replace("{width}", "100").replace("{height}", "100") if user_data else None
                
                if data["data"]:
                    # Streamer is live
                    current_title = data["data"][0]["title"]
                    is_live = True
                else:
                    # Streamer is offline, use stored channel "title"
                    current_title = user_data["title"] if user_data else "No title available"
                    is_live = False

                if current_title != last_titles[streamer]:
                    last_titles[streamer] = current_title
                    embed = make_embed(streamer, current_title, is_live, profile_image_url)
                    channel = bot.get_channel(info["channel_id"])
                    if info["ping"]:
                        await channel.send(f"@everyone {'🔴' if is_live else '⚫'} {streamer} changed stream title:", embed=embed)
                    else:
                        await channel.send(embed=embed)

        except Exception as e:
            print(f"Error in check_title_loop: {e}")
        await asyncio.sleep(60)  # Check every 60 seconds

bot.run(TOKEN)
