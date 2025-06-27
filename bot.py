import discord
import aiohttp
import asyncio
import os

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID_PING = int(os.environ["CHANNEL_ID_PING"])
CHANNEL_ID_NO_PING = int(os.environ["CHANNEL_ID_NO_PING"])

TWITCH_CLIENT_ID = os.environ["TWITCH_CLIENT_ID"]
TWITCH_CLIENT_SECRET = os.environ["TWITCH_CLIENT_SECRET"]

STREAMERS = {
    "jasontheween": {"channel_id": CHANNEL_ID_PING, "ping": True},
    "stableronaldo": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "adapt": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "plaqueboymax": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "silky": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
    "lacy": {"channel_id": CHANNEL_ID_NO_PING, "ping": False},
}

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

access_token = None
last_titles = {streamer: None for streamer in STREAMERS}
last_status = {streamer: None for streamer in STREAMERS}

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
    url = f"https://api.twitch.tv/helix/channels?broadcaster_login={username}"
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {access_token}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
            return data["data"][0] if data["data"] else None

def make_embed(username, title, is_live, profile_image_url):
    color = discord.Color.red() if is_live else discord.Color.dark_grey()
    embed = discord.Embed(
        title=f"{username}",
        description=title,
        color=color
    )
    if profile_image_url:
        embed.set_thumbnail(url=profile_image_url)
    embed.set_footer(text="🔴 LIVE" if is_live else "⚫ OFFLINE")
    return embed

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await get_twitch_token()
    bot.loop.create_task(check_title_loop())

async def check_title_loop():
    global last_titles, last_status
    await bot.wait_until_ready()

    while not bot.is_closed():
        for streamer, info in STREAMERS.items():
            try:
                stream_data = await get_stream_data(streamer)
                user_data = await get_user_data(streamer)
                profile_image_url = user_data["thumbnail_url"].replace("{width}", "100").replace("{height}", "100") if user_data else None

                is_live = bool(stream_data["data"])
                current_title = (
                    stream_data["data"][0]["title"] if is_live
                    else user_data["title"] if user_data
                    else "No title available"
                )

                normalized_title = current_title.strip().lower()
                last_normalized = (last_titles[streamer] or "").strip().lower()
                status_changed = last_status[streamer] != is_live

                if normalized_title != last_normalized or status_changed:
                    last_titles[streamer] = current_title
                    last_status[streamer] = is_live
                    embed = make_embed(streamer, current_title, is_live, profile_image_url)
                    channel = bot.get_channel(info["channel_id"])
                    if info["ping"]:
                        await channel.send(f"@everyone {'🔴' if is_live else '⚫'} {streamer} changed stream title:", embed=embed)
                    else:
                        await channel.send(embed=embed)

            except Exception as e:
                print(f"Error with {streamer}: {e}")
        await asyncio.sleep(60)

bot.run(TOKEN)

