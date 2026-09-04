import os
import random
import asyncio
import datetime

import discord
from discord import app_commands
from discord.ext import commands
import wavelink
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)  # prefix unused; slash only


STATUSES = [
    "hi :3",
    "The FitnessGram pacer test",
    "fard 💨",
    "bye >:3",
    "guess whos backkkk!!!",
    "Good Threads before good threads",
    "geez i miss 2021",
    "We using slash commands now?!?!",
    "Hello World by Louie Zong",
    "Never Gonna Give You Up by Rick Astley",
]

LAVALINK_HOST = "lava2.kasawa.pro"
LAVALINK_PORT = 2334
LAVALINK_PASSWORD = "youshallnotpass"
LAVALINK_SECURE = False


async def ch_pr():
    await bot.wait_until_ready()
    while not bot.is_closed():
        status = random.choice(STATUSES)
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=status,
            )
        )
        await asyncio.sleep(10)


async def node_connect():
    await bot.wait_until_ready()
    scheme = "https" if LAVALINK_SECURE else "http"
    uri = f"{scheme}://{LAVALINK_HOST}:{LAVALINK_PORT}"
    print(f"Connecting to Lavalink at {uri} ...")
    try:
        node = wavelink.Node(uri=uri, password=LAVALINK_PASSWORD)
        await wavelink.Pool.connect(client=bot, nodes=[node])
        print("Pool.connect() finished (waiting for node ready event)...")
    except Exception as e:
        print(f"Lavalink connect FAILED: {e!r}")


async def search_tracks(query: str) -> wavelink.Search:
    sources = [
        wavelink.TrackSource.YouTube,
        wavelink.TrackSource.YouTubeMusic,
        wavelink.TrackSource.SoundCloud,
        None,
    ]
    last_err: Exception | None = None
    for source in sources:
        try:
            if source is None:
                results = await wavelink.Playable.search(query)
            else:
                results = await wavelink.Playable.search(query, source=source)
            if results:
                print(f"search OK source={source}")
                return results
        except wavelink.LavalinkLoadException as e:
            last_err = e
            print(f"search failed source={source}: {e}")
            continue
        except Exception as e:
            last_err = e
            print(f"search failed source={source}: {e!r}")
            continue
    if last_err is not None:
        raise last_err
    return []


def get_vc(interaction: discord.Interaction) -> wavelink.Player | None:
    if interaction.guild is None:
        return None
    return interaction.guild.voice_client  # type: ignore[return-value]


async def get_player_or_error(
    interaction: discord.Interaction,
    command_name: str,
    *,
    require_playing: bool = True,
) -> wavelink.Player | None:
    vc = get_vc(interaction)
    if vc is None:
        await interaction.followup.send(
            f"Nothing is currently playing, therefore you cannot use `/{command_name}`",
            ephemeral=True,
        )
        return None
    if require_playing and not vc.playing:
        await interaction.followup.send(
            f"Nothing is currently playing, therefore you cannot use `/{command_name}`",
            ephemeral=True,
        )
        return None
    return vc


def now_playing_embed(track: wavelink.Playable) -> discord.Embed:
    em = discord.Embed(
        title="*Now Playing*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name=f"`{track.title}`",
        value=f"**By**: `{track.author}`",
    )
    return em


@bot.event
async def on_ready():
    print("a new start")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"Slash sync failed: {e!r}")
    bot.loop.create_task(node_connect())
    bot.loop.create_task(ch_pr())


@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"Node {payload.node.identifier} is ready!!!!, less gooo")


@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    vc = payload.player
    track = payload.original or payload.track
    print(f"TRACK START: {getattr(track, 'title', track)}")
    if vc is None or track is None:
        return
    channel = getattr(vc, "announce_channel", None)
    if channel is None:
        return
    if getattr(vc, "_announce_next", False):
        em = discord.Embed(
            title="*Next Playing*",
            color=discord.Color.from_rgb(255, 255, 255),
        )
        em.add_field(
            name=f"`{track.title}`",
            value=f"**By**: `{track.author}`",
        )
        try:
            await channel.send(embed=em)
        except Exception as e:
            print(f"announce failed: {e!r}")
    vc._announce_next = True


@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    print(f"TRACK END: reason={payload.reason}")


@bot.event
async def on_wavelink_track_exception(payload: wavelink.TrackExceptionEventPayload):
    err = payload.exception
    msg = str(err.get("message") if isinstance(err, dict) else err)
    msg = msg.replace("\n", " ")[:200]
    print(f"TRACK EXCEPTION: {msg}")
    vc = payload.player
    channel = getattr(vc, "announce_channel", None) if vc else None
    if channel is not None:
        try:
            await channel.send(f"Track failed to play: `{msg}`")
        except Exception:
            pass


@bot.event
async def on_wavelink_track_stuck(payload: wavelink.TrackStuckEventPayload):
    print(f"TRACK STUCK: threshold={payload.threshold}")


@bot.tree.command(name="more", description="Sends my website link")
async def more(interaction: discord.Interaction):
    await interaction.response.send_message("https://myokaylinkssite.netlify.app/")


@bot.tree.command(name="play", description="Play a song or resume if paused")
@app_commands.describe(search="Song name or URL (leave empty to resume if paused)")
async def play(interaction: discord.Interaction, search: str | None = None):
    await interaction.response.defer()

    vc = get_vc(interaction)

    if not search or not search.strip():
        if vc is not None and vc.paused:
            await vc.pause(False)
            return await interaction.followup.send("***➤ Resumed***")
        return await interaction.followup.send(
            "Usage: `/play <song name or url>`\n"
            "Or `/play` with no args while paused to resume.",
            ephemeral=True,
        )

    if not getattr(interaction.user.voice, "channel", None):
        return await interaction.followup.send(
            "You are not in a vc, therefore you cannot use `/play`",
            ephemeral=True,
        )

    try:
        wavelink.Pool.get_node()
    except wavelink.InvalidNodeException:
        return await interaction.followup.send(
            "Lavalink node is not connected yet (or is offline). "
            "Wait a few seconds or check the console.",
            ephemeral=True,
        )

    try:
        tracks = await search_tracks(search)
    except wavelink.LavalinkLoadException as e:
        return await interaction.followup.send(
            f"Node failed to load tracks for `{search}`.\n`{e}`"[:500]
        )
    except Exception as e:
        return await interaction.followup.send(f"Search error: `{e!r}`")

    if not tracks:
        return await interaction.followup.send(f"No tracks found for `{search}`")

    if not vc:
        try:
            vc = await interaction.user.voice.channel.connect(
                cls=wavelink.Player,
                self_deaf=True,
                timeout=60.0,
            )
        except Exception as e:
            return await interaction.followup.send(
                f"Couldn't join your voice channel: `{type(e).__name__}: {e}`"
            )
    else:
        vc = get_vc(interaction)

    vc.autoplay = wavelink.AutoPlayMode.partial
    vc.announce_channel = interaction.channel
    if not hasattr(vc, "_announce_next"):
        vc._announce_next = False

    await vc.set_volume(100)
    actively_playing = vc.playing and not vc.paused

    if isinstance(tracks, wavelink.Playlist):
        added = await vc.queue.put_wait(tracks)
        await interaction.followup.send(
            f"***➤ Added playlist `{tracks.name}` ({added} tracks) to the queue***"
        )
        if not actively_playing:
            vc._announce_next = False
            if vc.paused and vc.current is not None:
                await vc.skip(force=True)
            elif not vc.playing:
                await vc.play(vc.queue.get(), paused=False)
            if vc.paused:
                await vc.pause(False)
            if vc.current is not None:
                await interaction.followup.send(embed=now_playing_embed(vc.current))
        return

    track: wavelink.Playable = tracks[0]
    print(f"resolved track title={track.title!r} uri={getattr(track, 'uri', None)}")

    if actively_playing:
        await vc.queue.put_wait(track)
        return await interaction.followup.send(
            f"***➤ Added `{track.title}` to the queue***"
        )

    vc._announce_next = False
    await vc.queue.put_wait(track)

    if vc.paused and vc.current is not None:
        await vc.skip(force=True)
        if vc.paused:
            await vc.pause(False)
    elif not vc.playing:
        await vc.play(vc.queue.get(), paused=False)
    else:
        await vc.pause(False)

    await interaction.followup.send(embed=now_playing_embed(track))


@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = await get_player_or_error(interaction, "pause")
    if vc is None:
        return
    if vc.paused:
        return await interaction.followup.send("Already paused.", ephemeral=True)

    await vc.pause(True)
    em = discord.Embed(title="*Paused*", color=discord.Color.from_rgb(255, 255, 255))
    em.add_field(
        name="*we `paused` your song for ya*",
        value="either use `/play` or `/resume` to unpause",
    )
    await interaction.followup.send(embed=em)


@bot.tree.command(name="resume", description="Resume the paused song")
async def resume(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = await get_player_or_error(interaction, "resume", require_playing=True)
    if vc is None:
        return
    if not vc.paused:
        return await interaction.followup.send("Not paused.", ephemeral=True)

    await vc.pause(False)
    em = discord.Embed(title="*Resumed*", color=discord.Color.from_rgb(255, 255, 255))
    em.add_field(
        name="*we `resumed` your song for ya*",
        value="enjoy ur song.. ig BAKA",
    )
    await interaction.followup.send(embed=em)


@bot.tree.command(name="stop", description="Stop playback and clear the queue")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = await get_player_or_error(interaction, "stop")
    if vc is None:
        return

    vc.queue.mode = wavelink.QueueMode.normal
    vc.queue.clear()
    await vc.skip(force=True)

    em = discord.Embed(title="*Stopped*", color=discord.Color.from_rgb(255, 255, 255))
    em.add_field(
        name="*we `stopped` your song for ya*",
        value="use `/play` and a song of ur choice to start it up again",
    )
    await interaction.followup.send(embed=em)


@bot.tree.command(name="disconnect", description="Make the bot leave the voice channel")
async def disconnect(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = get_vc(interaction)
    if vc is None:
        return await interaction.followup.send(
            "I'm not in a vc, therefore you cannot use `/disconnect`",
            ephemeral=True,
        )

    await vc.disconnect()
    em = discord.Embed(
        title="*Disconnected*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="*the bot has been `disconnected`*",
        value="type `/play` and a song of choice to invite it back :]",
    )
    await interaction.followup.send(embed=em)


@bot.tree.command(name="loop", description="Toggle looping the current song")
async def loop(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = await get_player_or_error(interaction, "loop")
    if vc is None:
        return

    if vc.queue.mode is wavelink.QueueMode.loop:
        vc.queue.mode = wavelink.QueueMode.normal
        title = vc.current.title if vc.current else "your song"
        await interaction.followup.send(
            f'***➤ "`{title}`" is no longer looping***'
        )
    else:
        vc.queue.mode = wavelink.QueueMode.loop
        await interaction.followup.send("***➤ Now looping your song***")


@bot.tree.command(name="skip", description="Skip to the next song in the queue")
async def skip(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = await get_player_or_error(interaction, "skip")
    if vc is None:
        return

    await vc.skip(force=True)
    if vc.paused:
        await vc.pause(False)

    em = discord.Embed(title="*skipped*", color=discord.Color.from_rgb(255, 255, 255))
    em.add_field(name="*we `skipped` your song for ya*", value=":p")
    await interaction.followup.send(embed=em)


@bot.tree.command(name="queue", description="Show the queued songs")
async def queue(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = get_vc(interaction)
    if vc is None:
        return await interaction.followup.send(
            "You are not in a vc, therefore you cannot use `/queue`",
            ephemeral=True,
        )

    if vc.queue.is_empty:
        return await interaction.followup.send("*thy **`Queue`** is empty*")

    songs = list(vc.queue)
    total = len(songs)
    limit = 20
    lines = [
        f"`{i}.` {(s.title or 'Unknown')[:80]}"
        for i, s in enumerate(songs[:limit], start=1)
    ]
    desc = "\n".join(lines)
    if total > limit:
        desc += f"\n\n...and **{total - limit}** more"

    em = discord.Embed(
        title=f"***Queue***",
        description=desc,
        color=discord.Color.from_rgb(46, 49, 54),
    )
    if vc.current is not None:
        em.set_footer(text=f"𝘗𝘭𝘢𝘺𝘪𝘯𝘨 𝘯𝘰𝘸: {vc.current.title}")
    await interaction.followup.send(embed=em)



@bot.tree.command(name="remove", description="Remove a track from the queue by its number")
@app_commands.describe(number="Queue position to remove, see /queue")
async def remove(interaction: discord.Interaction, number: app_commands.Range[int, 1, 1000]):
    try:
        await interaction.response.defer()
    except discord.NotFound:
        return

    vc = get_vc(interaction)
    if vc is None:
        return await interaction.followup.send(
            "I'm not in a vc and or nothing is queued.",
            ephemeral=True,
        )

    if vc.queue.is_empty:
        return await interaction.followup.send(
            "Queue is empty nothing to remove.",
            ephemeral=True,
        )

    songs = list(vc.queue)
    if number > len(songs):
        return await interaction.followup.send(
            f"Invalid number. Queue only has **{len(songs)}** track(s). Use `/queue` to check.",
            ephemeral=True,
        )

    removed = songs.pop(number - 1)  

   
    vc.queue.clear()
    for song in songs:
        await vc.queue.put_wait(song)

    await interaction.followup.send(
        f"***➤ Removed `{removed.title}` from the queue***"
    )


@bot.tree.command(name="info", description="Show info on the current song")
async def info(interaction: discord.Interaction):
    await interaction.response.defer()
    vc = await get_player_or_error(interaction, "info")
    if vc is None:
        return

    track = vc.current
    if track is None:
        return await interaction.followup.send("Nothing is currently playing.")

    em = discord.Embed(
        title="***Info***",
        description=f"➤ **Artist:** \n `{track.author}`",
        color=discord.Color.from_rgb(100, 108, 245),
    )
    em.add_field(
        name="➤ Length:",
        value=f"`{str(datetime.timedelta(milliseconds=track.length))}`",
    )
    em.add_field(name="➤ Paused:", value=f"`{vc.paused}`")
    em.add_field(name="➤ Playing:", value=f"`{vc.playing}`")
    if track.uri:
        em.add_field(
            name="Extra Info:",
            value=f"[Click me for original]({track.uri})",
        )
    await interaction.followup.send(embed=em)


@bot.tree.command(name="help", description="Show bot commands")
async def help_cmd(interaction: discord.Interaction):
    em = discord.Embed(
        title="`slash commands:`",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="**/play**:",
        value="`/play <song>` plays/queues and just `/play` resumes if paused",
        inline=False,
    )
    em.add_field(name="**/remove**:", value="`/remove <number>` removes that song from the queue (see `/queue` for numbers)", inline=False,)
    em.add_field(name="**/pause**:", value="pauses the current song", inline=False)
    em.add_field(name="**/resume**:", value="resumes a paused song", inline=False)
    em.add_field(name="**/stop**:", value="stops playback and clears the queue", inline=False)
    em.add_field(name="**/skip**:", value="skips to the next song in queue", inline=False)
    em.add_field(name="**/disconnect**:", value="makes MpFree leave the vc", inline=False)
    em.add_field(
        name="**/loop**:",
        value="loops current song, run again to stop looping",
        inline=False,
    )
    em.add_field(name="**/queue**:", value="shows queued songs", inline=False)
    em.add_field(name="**/info**:", value="info on the song being played", inline=False)
    em.add_field(name="**/more**:", value="sends my website", inline=False)
    await interaction.response.send_message(embed=em)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Missing DISCORD_TOKEN in .env")
    bot.run(token)