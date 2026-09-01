import os
import random
import asyncio
import datetime

import discord
from discord.ext import commands
import wavelink

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="m", intents=intents)
bot.remove_command("help")




STATUSES = [
    "hi :3",
    "The FitnessGram pacer test",
    "fard 💨",
    "bye >:3",
    "guess whos backkkk!!!",
    "Good Threads before good threads"
]

LAVALINK_HOST = "lavalinkv4.serenetia.com"
LAVALINK_PORT = 80
LAVALINK_PASSWORD = "https://seretia.link/discord"
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
        node = wavelink.Node(
            uri=uri,
            password=LAVALINK_PASSWORD,
        )
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


async def get_player_or_error(
    ctx: commands.Context,
    command_name: str,
    *,
    require_playing: bool = True,
):
    vc: wavelink.Player | None = ctx.voice_client
    if vc is None:
        await ctx.reply(
            f"Nothing is currently playing, therefore you cannot invoke `m{command_name}`",
            mention_author=False,
        )
        return None
    if require_playing and not vc.playing:
        await ctx.reply(
            f"Nothing is currently playing, therefore you cannot invoke `m{command_name}`",
            mention_author=False,
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
    if vc is None:
        return
    ctx = getattr(vc, "ctx", None)
    if ctx is None or track is None:
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
        await ctx.reply(embed=em, mention_author=False)
    vc._announce_next = True


@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    print(f"TRACK END: reason={payload.reason}")


@bot.event
async def on_wavelink_track_exception(payload: wavelink.TrackExceptionEventPayload):
    print(f"TRACK EXCEPTION: {payload.exception}")
    vc = payload.player
    ctx = getattr(vc, "ctx", None) if vc else None
    if ctx is not None:
        await ctx.reply(
            f"Track failed to play: `{payload.exception}`",
            mention_author=False,
        )


@bot.event
async def on_wavelink_track_stuck(payload: wavelink.TrackStuckEventPayload):
    print(f"TRACK STUCK: threshold={payload.threshold}")


@bot.command()
async def more(ctx):
    await ctx.send("https://myokaylinkssite.netlify.app/")

@bot.command(aliases=["Play","p","P"])
async def play(ctx: commands.Context, *, search: str | None = None):

    vc: wavelink.Player | None = ctx.voice_client

    if not search or not search.strip():
        if vc is not None and vc.paused:
            await vc.pause(False)
            return await ctx.reply(
                "***~Resumed~***",
                mention_author=False,
            )
        return await ctx.reply(
            "Usage: `mplay <song name or url>`\n"
            "Or `mplay` with no args while paused to resume.",
            mention_author=False,
        )

    if not getattr(ctx.author.voice, "channel", None):
        return await ctx.reply(
            "You are not in a vc, therefore, you cannot invoke the `mplay` command",
            mention_author=False,
        )

    try:
        wavelink.Pool.get_node()
    except wavelink.InvalidNodeException:
        return await ctx.reply(
            "Lavalink node is not connected yet (or is offline). "
            "Wait a few seconds or check the console.",
            mention_author=False,
        )

    try:
        tracks = await search_tracks(search)
    except wavelink.LavalinkLoadException as e:
        return await ctx.reply(
            f"Node failed to load tracks for `{search}`.\n`{e}`",
            mention_author=False,
        )
    except Exception as e:
        return await ctx.reply(f"Search error: `{e!r}`", mention_author=False)

    if not tracks:
        return await ctx.reply(
            f"No tracks found for `{search}`",
            mention_author=False,
        )

    if not ctx.voice_client:
        vc = await ctx.author.voice.channel.connect(
            cls=wavelink.Player,
            self_deaf=True,
        )
    else:
        vc = ctx.voice_client

    vc.autoplay = wavelink.AutoPlayMode.partial
    vc.ctx = ctx
    if not hasattr(vc, "_announce_next"):
        vc._announce_next = False

    await vc.set_volume(100)

    actively_playing = vc.playing and not vc.paused

    if isinstance(tracks, wavelink.Playlist):
        added = await vc.queue.put_wait(tracks)
        await ctx.reply(
            f"***~Added playlist `{tracks.name}` ({added} tracks) to the queue~***",
            mention_author=False,
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
                await ctx.reply(
                    embed=now_playing_embed(vc.current),
                    mention_author=False,
                )
        return

    track: wavelink.Playable = tracks[0]
    print(f"resolved track title={track.title!r} uri={getattr(track, 'uri', None)}")

    if actively_playing:
        await vc.queue.put_wait(track)
        await ctx.reply(
            f"***~Added `{track.title}` to the queue~***",
            mention_author=False,
        )
        return

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

    await ctx.reply(embed=now_playing_embed(track), mention_author=False)


@bot.command(aliases=["Pause"])
async def pause(ctx: commands.Context):
    vc = await get_player_or_error(ctx, "pause")
    if vc is None:
        return
    if vc.paused:
        return await ctx.reply("Already paused.", mention_author=False)

    await vc.pause(True)
    em = discord.Embed(
        title="*~Paused~*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="*we `paused` your song for ya*",
        value="you better be grateful",
    )
    await ctx.reply(embed=em, mention_author=False)


# NOTE: do NOT alias this as "Play" — conflicts with mplay (case-insensitive)
@bot.command(aliases=["Resume","Unpause","unpause"])
async def resume(ctx: commands.Context):
    vc = await get_player_or_error(ctx, "resume", require_playing=True)
    if vc is None:
        return
    if not vc.paused:
        return await ctx.reply("Not paused.", mention_author=False)

    await vc.pause(False)
    em = discord.Embed(
        title="*~Resumed~*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="*we `resumed` your song for ya*",
        value="you better be grateful",
    )
    await ctx.reply(embed=em, mention_author=False)


@bot.command(aliases=["STAP"])
async def stop(ctx: commands.Context):
    vc = await get_player_or_error(ctx, "stop")
    if vc is None:
        return

    vc.queue.mode = wavelink.QueueMode.normal
    vc.queue.clear()
    await vc.skip(force=True)

    em = discord.Embed(
        title="*~Stopped~*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="*we `stopped` your song for ya*",
        value="you better be grateful",
    )
    await ctx.reply(embed=em, mention_author=False)


@bot.command(aliases=["kys", "die","kill","leave","kill your self"])
async def disconnect(ctx: commands.Context):
    vc: wavelink.Player | None = ctx.voice_client
    if vc is None:
        return await ctx.reply(
            "I'm not in a vc, therefore, you cannot invoke the `t.disconnect` command",
            mention_author=False,
        )

    await vc.disconnect()
    em = discord.Embed(
        title="*~Disconnected~*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="*the bot has been `disconnected`*",
        value="type in mplay and a song of choice to invite it back :]",
    )
    await ctx.reply(embed=em, mention_author=False)


@bot.command()
async def loop(ctx: commands.Context):
    vc = await get_player_or_error(ctx, "loop")
    if vc is None:
        return

    if vc.queue.mode is wavelink.QueueMode.loop:
        vc.queue.mode = wavelink.QueueMode.normal
        title = vc.current.title if vc.current else "your song"
        await ctx.reply(
            f'***"`{title}`" is no longer looping***',
            mention_author=False,
        )
    else:
        vc.queue.mode = wavelink.QueueMode.loop
        await ctx.reply(
            "***Now looping your song***",
            mention_author=False,
        )


@bot.command()
async def skip(ctx: commands.Context):
    vc = await get_player_or_error(ctx, "skip")
    if vc is None:
        return

    await vc.skip(force=True)
    if vc.paused:
        await vc.pause(False)

    em = discord.Embed(
        title="*skipped*",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="*we `skipped` your song for ya*",
        value=":p",
    )
    await ctx.reply(embed=em, mention_author=False)


@bot.command(aliases=['q','Q'])
async def queue(ctx: commands.Context):
    vc: wavelink.Player | None = ctx.voice_client
    if vc is None:
        return await ctx.reply(
            "You are not in a vc, therefore, you cannot invoke the `mqueue` command",
            mention_author=False,
        )

    if vc.queue.is_empty:
        return await ctx.reply(
            "***thy `Queue` is empty***",
            mention_author=False,
        )

    em = discord.Embed(
        title="***Queue***",
        color=discord.Color.from_rgb(46, 49, 54),
    )
    for song_count, song in enumerate(vc.queue, start=1):
        em.add_field(
            name=f"Song: `{song_count}`",
            value=f"`{song.title}`",
            inline=False,
        )
    await ctx.reply(embed=em, mention_author=False)


@bot.command()
async def info(ctx: commands.Context):
    vc = await get_player_or_error(ctx, "info")
    if vc is None:
        return

    track = vc.current
    if track is None:
        return await ctx.reply(
            "Nothing is currently playing.",
            mention_author=False,
        )

    em = discord.Embed(
        title="***>Info<***",
        description=f"**Artist:** \n `{track.author}`",
        color=discord.Color.from_rgb(100, 108, 245),
    )
    em.add_field(
        name="Length:",
        value=f"`{str(datetime.timedelta(milliseconds=track.length))}`",
    )
    em.add_field(name="Paused:", value=f"`{vc.paused}`")
    em.add_field(name="Playing:", value=f"`{vc.playing}`")
    if track.uri:
        em.add_field(
            name="Extra Info:",
            value=f"[Click me for original]({track.uri})",
        )
    await ctx.send(embed=em)


@bot.command(aliases=["HELP", "hep", "h", "H"])
async def help(ctx: commands.Context):
    em = discord.Embed(
        title="`commands:`",
        color=discord.Color.from_rgb(255, 255, 255),
    )
    em.add_field(
        name="**play** `or p`:",
        value="`mplay <song>` plays/queues · bare `mplay` resumes if paused",
        inline=False,
    )
    em.add_field(
        name="**pause**:",
        value="pauses song that is being played",
        inline=False,
    )
    em.add_field(
        name="**resume** `or unpause`:",
        value="resumes song that was paused",
        inline=False,
    )
    em.add_field(
        name="**stop**:",
        value="stops playback and clears the queue",
        inline=False,
    )
    em.add_field(
        name="**skip**:",
        value="makes MpFree skip to the next song in queue",
        inline=False,
    )
    em.add_field(
        name="**disconnect** `or kill`:",
        value="makes MpFree leave the vc",
        inline=False,
    )
    em.add_field(
        name="**loop**:",
        value="loops song that is being played, send `command` again to stop looping song",
        inline=False,
    )
    em.add_field(
        name="**queue** `or q`:",
        value="shows queued songs",
        inline=False,
    )
    em.add_field(
        name="**info**:",
        value="shows info on the song being played",
        inline=False,
    )
    em.add_field(
        name="**more**:",
        value="literally just sends you my website lmao",
        inline=False,
    )
    await ctx.send(embed=em)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Missing DISCORD_TOKEN in .env")
    bot.run(token)