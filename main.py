import discord
from discord.ui import Button, View
from discord.ext import commands
import wavelink
import os

TOKEN=os.getenv("TOKEN")
PREFIX = "%"
client=commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())
client.remove_command("help")

@client.event
async def on_ready():
    print("ONLINE")
    await client.load_extension("music")
    print(f"Logged in as {client.user}")
    nodes = [wavelink.Node(uri="http://lavalinkv4.serenetia.com:80",password="youshallnotpass")]
    await wavelink.NodePool.connect(client=client, nodes=nodes)
    print("Lavalink Node Connected.")
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name=f"{PREFIX}help"))

# ---------------- RUN BOT ---------------- #

music_commands = {
    "join": "Joins the voice channel that the user is currently in.",
    "play": "Plays a song from a YouTube URL or by searching a title.",
    "pause": "Pauses the currently playing song.",
    "skip": "Skips the current song and plays the next in queue.",
    "stop": "Stops playback and clears the queue.",
    "nowplaying": "Shows the song that is currently playing.",
    "queue": "Displays the list of upcoming songs.",
    "remove": "Removes a specific song from the queue by its index."
}


@client.command()
async def help(ctx):
    owner=client.get_user(917591713793605702)
    embed=discord.Embed(title="Music",
                        description=f">>> **Hey! This is {client.user.mention} a cool music bot with simple commands. The commands that can be used are**",color=0x262338)
    for i in music_commands:
        embed.add_field(name=f"`{PREFIX}{i}`",value=music_commands[i],inline=False)
    embed.set_thumbnail(url=client.user.avatar.url)
    embed.set_footer(text=f"Made with 💖", icon_url=owner.avatar.url)
    button1 = Button(label="invite",
    style=discord.ButtonStyle.blurple,
                     url=f"https://discord.com/api/oauth2/authorize?client_id={client.user.id}&permissions=8&scope=bot")
    view = View()
    view.add_item(button1)
    await ctx.reply(embed=embed, mention_author=False, view=view)

client.run(TOKEN)
