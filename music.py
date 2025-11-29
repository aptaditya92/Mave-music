import discord
from discord.ext import commands
import wavelink
import requests
import re
import json
import urllib.parse

#•Helpers=================================

def get_duration(duration: int):
    minutes, seconds = divmod(duration // 1000, 60)
    return f"{minutes}:{seconds:02d}"
    
def get_position(position: int):
    minutes, seconds = divmod(position // 1000, 60)
    return f"{minutes}:{seconds:02d}"

def build_progress_bar(position: int, duration: int, length: int = 20):
    filled = int((position / duration) * length)
    empty = length - filled
    #━❍────────

    bar = "━" * filled + "❍" + "─" * empty

    return f"`{bar}`\n"

def fetchurl(search_query):
    query = urllib.parse.quote(search_query)
    url = f"https://www.youtube.com/results?search_query={query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    match = re.search(r"var ytInitialData = ({.*?});", response.text)

    if not match:
        return None

    data = json.loads(match.group(1))

    try:
        contents = (
            data["contents"]["twoColumnSearchResultsRenderer"]["primaryContents"]
            ["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"]
        )

        for item in contents:
            if "videoRenderer" in item:
                video_id = item["videoRenderer"]["videoId"]
                return f"https://www.youtube.com/watch?v={video_id}"

    except Exception as e:
        print("Error parsing:", e)

    return None

#•Music=============================

class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.skip_votes = {}
        self.autoplay_enabled = {}

    async def send_embed(self, ctx, description):
        embed = discord.Embed(description=description, color=0x262338)
        return await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Music Cog Loaded as {self.client.user}")
        nodes = [
            wavelink.Node(
                uri="http://lavalinkv4.serenetia.com:80",
                password="youshallnotpass"
            )
        ]
        await wavelink.Pool.connect(client=self.client, nodes=nodes)
        print("Lavalink Node Connected.")
        await self.client.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="Music"))

    @commands.command(aliases=["connect"])
    async def join(self, ctx):
        if ctx.author.voice is None:
            return await self.send_embed(ctx, "⚠️ Join a voice channel first.")

        vc = ctx.author.voice.channel
        await vc.connect(cls=wavelink.Player)
        await self.send_embed(ctx, f"✅ Connected to **{vc}**")

    @commands.command(aliases=["resume"])
    async def pause(self, ctx):
        if not ctx.voice_client:
            return await self.send_embed(ctx, "⚠️ Make sure you or I are connected to a voice channel.")
        vc: wavelink.Player = ctx.voice_client

        if vc.paused:
            await vc.pause(False)
            await self.send_embed(ctx, "▶️ Playback: **Resumed**")
        else:
            await vc.pause(True)
            await self.send_embed(ctx, "⏸️ Playback: **Paused**")

    @commands.command(aliases=["r"])
    async def remove(self, ctx, index: int):
        if not ctx.voice_client:
            return await self.send_embed(ctx, "⚠️ Make sure you are connected to a voice channel.")
        else:
            player: wavelink.Player = ctx.voice_client
            if index > 0 and index <= len(player.queue):
                track = player.queue[index-1]
                del player.queue[index-1]
                await self.send_embed(ctx, f"🗑️ Removed **[{track.title}]({track.uri})** from queue. Songs left: {len(player.queue)}")
        

    
    @commands.command(aliases=["p","add"])
    async def play(self, ctx, *, query: str):

        if not ctx.voice_client:
            await self.join(ctx)

        if ctx.author.voice is None:
            return await ctx.send("Join a voice channel first.")

        if "https://" not in query:
            search = fetchurl(query)
        else:
            search = query

        player: wavelink.Player = ctx.voice_client
        vc = player
        if "spotify.com/playlist" in query:
            tracks = await wavelink.Playable.search(query)
            await self.send_embed(ctx, f"💾 Loaded playlist: **[{tracks.name}]({query})** with `{len(tracks.tracks)}` songs")

            if tracks:
                if not player.playing:
                   await player.play(tracks[0])
                else:
                    await player.queue.put_wait(tracks[0])
                for track in tracks[1:]:
                    await player.queue.put_wait(track)


        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            return await self.send_embed(ctx,"❌ No result found.")

        track = tracks[0]

        if player.playing:
            await player.queue.put_wait(track)
            return await self.send_embed(ctx, f"🎶 Added **[{track.title}]({track.uri})** to queue at position **{len(player.queue)}**")
        else:
            await player.play(track)
            return await self.send_embed(ctx, f"🎶 Started playing: **[{track.title}]({track.uri})**")

    # ---------------------- QUEUE COMMAND ----------------------
    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        player: wavelink.Player = ctx.voice_client
        if player and player.playing:
            upcoming = player.queue.copy()
            embed = discord.Embed(color=0x262338)

            if upcoming:
                
                queue_list = "\n".join(
                    [f"{i+1}. 💿 [{get_duration(track.length)}] - **[{track.title}]({track.uri})**" for i, track in enumerate(upcoming[:10])]
                )
                embed.add_field(
                    name="Upcoming",
                    value=queue_list,
                    inline=False)
                embed.set_footer(text=f"{len(upcoming)} Songs in queue",icon_url=self.client.user.avatar.url)
                return await ctx.send(embed=embed)
            else:
                return await self.send_embed(ctx, "⚠️ No songs in queue.")


    @commands.command(aliases=["np","current","track","song"])
    async def nowplaying(self, ctx):
        player: wavelink.Player = ctx.voice_client

        if not player or not player.playing:
           return await self.send_embed(ctx, "⚠️ Nothing is playing right now.")

        current = player.current
        track = current
        position = player.position
        duration = current.length

        
        timestamp = f"{get_position(position)}/{get_duration(duration)}"
        progress_bar = build_progress_bar(position, duration)

        embed = discord.Embed(title="Now Playing 🎵",description=f"**[{track.title}]({track.uri})**\n\n{progress_bar}[{timestamp}]", color=0x262338)
        embed.add_field(name="Author", value=current.author)
        embed.set_thumbnail(url=current.artwork)

        await ctx.send(embed=embed)

    @commands.command(aliases=["s"])
    async def skip(self, ctx):
        player: wavelink.Player = ctx.voice_client

        if not player or not player.playing:
            return await ctx.send("Nothing is playing.")
        track = player.current

        if ctx.author.guild_permissions.administrator:
            await self.send_embed(ctx, f"⏩ Track **[{track.title}]({track.uri})** was Skipped by an **Admin**")
            return await player.skip()

        gid = ctx.guild.id
        voters = self.skip_votes.setdefault(gid, set())

        if ctx.author.id in voters:
            return await ctx.send("You already voted to skip!")

        voters.add(ctx.author.id)

        needed = max(1, int(len(ctx.guild.voice_client.channel.members) * 0.5))
        await self.send_embed(ctx, f"👥 Skip vote: `{len(voters)}/{needed}`")

        if len(voters) >= needed:
            self.skip_votes[gid] = set()
            await self.send_embed(ctx, f"⏩ Track **[{track.title}]({track.uri})** was voted to be Skipped")
            return await player.skip()

    @commands.command(aliases=["dc","leave","disconnect"])
    async def stop(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await self.send_embed(ctx, "✅ Ended queue and disconnected.")
        else:
            await self.send_embed(ctx, "⚠️ Bot is not connected") 

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if not player.queue.is_empty:
            if int(len(player.channel.members)) > 1:
                next_song = await player.queue.get_wait()
                await player.play(next_song)
                gid = player.channel.guild.id
                self.skip_votes[gid] = 0
            else:
                await player.disconnect()
        else:
            await player.disconnect()


async def setup(client):
    await client.add_cog(Music(client))