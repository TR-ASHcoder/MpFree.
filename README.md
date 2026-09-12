 <h1 align="center">💥 MpFree 💥</h1>

A free, self-hosted Discord music bot built with `discord.py` and `wavelink`. Play music from YouTube, YouTube Music, SoundCloud and Spotify ( kinda ) using slash commands.

## Features

-  Play tracks or full playlists via search or URL - YouTube, YouTube Music, and SoundCloud are searched directly, Spotify links are also supported if the connected Lavalink node has a Spotify-resolving plugin (e.g. [LavaSrc](https://github.com/topi314/LavaSrc)) enabled
-  Pause, resume, stop, skip, and loop playback
-  Paginated, interactive queue view (with prev/next buttons)
-  Shuffle and remove individual tracks from the queue
-  `/info` and `/ping` commands for track and latency details
- Fully slash-command based (no message prefix needed)

## Requirements

- Python 3.10+
- A Discord bot token
- Access to a Lavalink node (the bot connects to one via `wavelink`)

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/TR-ASHcoder/MpFree..git
   cd MpFree.
   ```

2. **Create a virtual environment (recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate    # macOS/Linux
   venv\Scripts\activate       # Windows
   ```

3. **Install dependencies**

   ```bash
   
   pip install -r requirements.txt
   ```

4. **Configure your environment**

   Copy `.env.example` to `.env` and add your Discord bot token:

   ```bash
   
   cp .env.example .env
   ```

   ```env
   
   DISCORD_TOKEN=your_bot_token_here
   ```

5. **Run the bot**

   ```bash
   
   python main.py
   ```

On startup, the bot syncs its slash commands and connects to its configured Lavalink node automatically.

> **Note:** The Lavalink host/port/password are currently hardcoded in `main.py` (`LAVALINK_HOST`, `LAVALINK_PORT`, `LAVALINK_PASSWORD`). If that public node goes offline or you'd rather run your own, update those values to point at your own [Lavalink](https://github.com/lavalink-devs/Lavalink) server.
>
> **Spotify:** Pasting a Spotify link into `/play` will only work if the Lavalink node you're connected to has a source plugin like LavaSrc installed and configured with Spotify API credentials. The bot's own search logic (`search_tracks()` in `main.py`) only queries YouTube, YouTube Music, and SoundCloud directly — Spotify resolution happens node-side, not in this codebase.

## Commands

| Command | Description |
|---|---|
| `/play <song>` | Plays a song/URL, or resumes if paused and run with no argument |
| `/pause` | Pauses the current song |
| `/resume` | Resumes a paused song |
| `/stop` | Stops playback and clears the queue |
| `/skip` | Skips to the next song in the queue |
| `/queue` | Shows the queued songs (paginated) |
| `/shuffle` | Randomizes the order of songs in the queue |
| `/remove <number>` | Removes a track from the queue by its position |
| `/loop` | Toggles looping of the current song |
| `/info` | Shows info about the currently playing song |
| `/disconnect` | Makes the bot leave the voice channel |
| `/ping` | Shows bot and Lavalink latency [ isnt in `/help` ] | 
| `/more` | Sends the developer's website link |
| `/help` | Lists all available commands |

## Tech Stack

- [discord.py](https://github.com/Rapptz/discord.py) — Discord API wrapper
- [wavelink](https://github.com/PythonistaGuild/Wavelink) — Lavalink client for audio playback
- [python-dotenv](https://github.com/theskumar/python-dotenv) — environment variable management

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
