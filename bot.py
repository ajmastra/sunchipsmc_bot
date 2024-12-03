import discord
from discord.ext import commands, tasks
import requests
import aiohttp
import io
import base64
import os

# Replace with your Discord bot token
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
API_URL = "https://api.mcsrvstat.us/3/sunchipsmc.com"

# Intents for the bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """Set the initial status when the bot is ready."""
    print(f"We have logged in as {bot.user}")
    update_server_status.start()  # Start the status updater loop

@tasks.loop(minutes=1)
async def update_server_status():
    """Periodically update the bot's status based on server status."""
    try:
        response = requests.get(API_URL)
        data = response.json()

        if data["online"]:
            players_online = data["players"]["online"]
            status_message = f"🟢 {players_online} players online @ sunchipsmc.com"
        else:
            status_message = "🔴 Server Offline"

        # Update the bot's status
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name=status_message)
        )
    except Exception as e:
        print(f"Error updating status: {e}")

@bot.command(name="status")
async def server_status(ctx):
    """Fetch server status."""
    try:
        response = requests.get(API_URL)
        data = response.json()
        
        if data["online"]:
            motd = " ".join(data["motd"]["clean"]) if "motd" in data else "Unknown"
            version = data.get("version", "Unknown")
            players_online = data["players"]["online"]
            max_players = data["players"]["max"]
            players_list = ", ".join([p["name"] for p in data["players"].get("list", [])])

            embed = discord.Embed(title="SunchipsMC Server Status", color=discord.Color.green())
            embed.add_field(name="MOTD", value="Sun Chips <3", inline=False)
            embed.add_field(name="Version", value=version, inline=True)
            embed.add_field(name="Players", value=f"{players_online}/{max_players}", inline=True)
            embed.add_field(name="Online Players", value=players_list or "None", inline=False)
            embed.add_field(name="Server Address", value="sunchipsmc.com", inline=False)
            embed.add_field(name="IP", value=data["ip"], inline=True)
            embed.add_field(name="Port", value=data["port"], inline=True)

           # Add server image if available
            if "icon" in data:
                # The icon is usually base64 encoded
                favicon_data = data["icon"].split(",")[1]
                server_icon = discord.File(io.BytesIO(base64.b64decode(favicon_data)), filename="server_icon.png")
                embed.set_thumbnail(url="attachment://server_icon.png")
                await ctx.send(embed=embed, file=server_icon)
            else:
                await ctx.send(embed=embed)
        else:
            await ctx.send("The server is currently offline.")
    except Exception as e:
        await ctx.send(f"Error fetching server status: {e}")

@bot.command(name="players")
async def online_players(ctx):
    """Fetch list of online players with their avatars."""
    try:
        response = requests.get(API_URL)
        data = response.json()

        if data["online"]:
            players = data["players"].get("list", [])
            
            if players:
                # Send the summary embed first
                summary_embed = discord.Embed(
                    title="Player Count",
                    description=f"Currently, {len(players)} players are online.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=summary_embed)
                
                # Process individual player embeds
                async with aiohttp.ClientSession() as session:
                    for player in players:
                        player_name = player["name"]
                        player_uuid = player["uuid"]
                        
                        # Use Crafatar API to fetch player avatar
                        avatar_url = f"https://crafatar.com/avatars/{player_uuid}?size=64&overlay=true"
                        profile_url = f"https://namemc.com/profile/{player_uuid}"

                        async with session.get(avatar_url) as avatar_response:
                            if avatar_response.status == 200:
                                avatar_data = io.BytesIO(await avatar_response.read())
                                avatar_file = discord.File(avatar_data, filename=f"{player_name}.png")
                                avatar_attachment_url = f"attachment://{player_name}.png"

                                # Create an embed for the player
                                embed = discord.Embed(
                                    title=f"{player_name}",
                                    color=discord.Color.blue()
                                )
                                embed.set_image(url=avatar_attachment_url)
                                embed.add_field(
                                    name="Profile",
                                    value=f"[View Profile]({profile_url})",
                                    inline=False
                                )

                                # Send the embed with the attached avatar file
                                await ctx.send(embed=embed, file=avatar_file)
            else:
                await ctx.send("No players are online.")
        else:
            await ctx.send("The server is currently offline.")
    except Exception as e:
        await ctx.send(f"Error fetching player list: {e}")


@bot.command(name="motd")
async def server_motd(ctx):
    """Fetch server's Message of the Day (MOTD)."""
    try:
        response = requests.get(API_URL)
        data = response.json()
        
        if "motd" in data:
            motd_clean = " ".join(data["motd"]["clean"])
            await ctx.send(f"Server MOTD: {motd_clean}")
        else:
            await ctx.send("MOTD is not available.")
    except Exception as e:
        await ctx.send(f"Error fetching MOTD: {e}")

# Run bot
bot.run(BOT_TOKEN)
