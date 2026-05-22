# musicdl

> **Your YouTube Music library, on your disk. Incrementally synced. Tagged. Done.**

A no-nonsense CLI to mirror your YouTube Music playlists — including private ones like **Liked Music** — into plain audio files you actually own. Built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp) and designed to be re-run on a schedule.

```bash
# One command. Run it weekly. Only new tracks get downloaded.
musicdl sync -o ./music -a mp3 -q 0 -j 8
```

---

## Why musicdl

There are a hundred YouTube downloaders. Most of them stop being useful the moment you want to:

- **Access your private playlists.** musicdl reads cookies straight from your browser — no manual `cookies.txt` exports, no re-login hassle. Liked Music works out of the box.
- **Keep a library in sync, not re-download it.** `sync` maintains an archive file: re-run it tomorrow, next week, or from cron, and only the new tracks come down. Think `rsync` for music.
- **Get files that don't look like garbage in your player.** Cover art and full metadata (title, artist, album) are embedded by default. No post-processing scripts.
- **Pick the format you actually want.** MP3 (VBR or CBR), M4A (no re-encoding — straight AAC out of YouTube), FLAC, OPUS, video MP4/MKV/WebM. Cap resolution if you need to.
- **Go fast.** `-j 8` runs eight downloads in parallel. A 500-track playlist finishes while you grab coffee.
- **Pull transcripts too.** Subtitles, lyrics tracks, auto-generated captions — single video or whole playlist, multiple languages.

Built for people who'd rather own their music library than rent access to it.

---

## Quick start

```bash
# 1. Install
uv tool install git+https://github.com/luis-codex/musicdl

# 2. Tell it which browser holds your YouTube Music session (once)
$env:MUSICDL_BROWSER = "firefox"   # PowerShell
# export MUSICDL_BROWSER=firefox   # bash/zsh

# 3. Mirror your Liked Music in MP3 320kbps with covers + metadata
musicdl sync -o ./music -a mp3 -q 0 -j 8

# 4. A week later, run the exact same command. Only new songs download.
musicdl sync -o ./music -a mp3 -q 0 -j 8
```

---

## Installation

Requires Python ≥ 3.14 (provisioned automatically by `uv`) and [`ffmpeg`](https://ffmpeg.org/) on your `PATH`.

```bash
# From GitHub (recommended)
uv tool install git+https://github.com/luis-codex/musicdl

# Or from a local clone
git clone https://github.com/luis-codex/musicdl
cd musicdl
uv tool install .
```

Once installed, `musicdl` is available globally:

```bash
musicdl --help
```

To upgrade:

```bash
uv tool install git+https://github.com/luis-codex/musicdl --reinstall
```

## Configure cookies

YouTube Music needs your cookies to access private playlists (Liked Music, Library, etc.). `musicdl` reads them straight from your browser — no exports, no manual files.

```bash
# Firefox (recommended on Windows)
musicdl --browser firefox list

# Others: chrome, brave, edge, opera, vivaldi, safari, chromium...
musicdl --browser chrome list
```

If you use a Firefox fork (Zen, Waterfox, LibreWolf) or a custom profile, pass the path explicitly:

```bash
musicdl --browser firefox --profile "C:\Users\<you>\AppData\Roaming\zen\Profiles\xxxx.Default" list
```

Or configure it once via environment variables:

| Variable                    | Default     | Example                                                                  |
| --------------------------- | ----------- | ------------------------------------------------------------------------ |
| `MUSICDL_BROWSER`           | `firefox`   | `chrome`                                                                 |
| `MUSICDL_BROWSER_PROFILE`   | *(empty)*   | `C:\Users\you\AppData\Roaming\zen\Profiles\xxxx.Default (release)`       |

**Windows (PowerShell)** — for the current session:

```powershell
$env:MUSICDL_BROWSER = "firefox"
$env:MUSICDL_BROWSER_PROFILE = "C:\Users\you\AppData\Roaming\zen\Profiles\xxxx.Default (release)"
```

To persist them across reboots (recommended), set them as User variables and open a **new** terminal:

```powershell
[Environment]::SetEnvironmentVariable("MUSICDL_BROWSER", "firefox", "User")
[Environment]::SetEnvironmentVariable("MUSICDL_BROWSER_PROFILE", "C:\Users\you\AppData\Roaming\zen\Profiles\xxxx.Default (release)", "User")
```

Alternative GUI: `Win + R` → `sysdm.cpl` → *Advanced* → *Environment Variables…* → add under *User variables*.

**macOS / Linux (bash/zsh)** — add to `~/.bashrc` or `~/.zshrc`:

```bash
export MUSICDL_BROWSER=firefox
export MUSICDL_BROWSER_PROFILE="$HOME/.mozilla/firefox/xxxx.default-release"
```

> ⚠️ **Windows + Chromium (Chrome/Brave/Edge):** since 2024 these browsers use **Application-Bound Encryption** and `yt-dlp` cannot decrypt their cookies ([yt-dlp#10927](https://github.com/yt-dlp/yt-dlp/issues/10927)). Use Firefox/Zen or export a `cookies.txt` manually.

## Commands

```bash
musicdl --help
```

### `list` — list playlist songs

```bash
# Your Liked Music (default)
musicdl list

# Another playlist
musicdl list "https://music.youtube.com/playlist?list=PLxxxx"
```

### `download` — download audio or video

Downloads a video or full playlist in the chosen format. Cover art and metadata are embedded by default.

```bash
# Default: M4A audio (no re-encoding, preserves the original AAC)
musicdl download "https://youtu.be/<id>"

# No URL → falls back to your Liked Music
musicdl download

# MP3 at 192 kbps
musicdl download "<url>" -a mp3 -q 192

# FLAC (lossless)
musicdl download "<url>" -a flac

# Video MP4 capped at 1080p
musicdl download "<url>" -t video -v mp4 --max-height 1080

# Full playlist into a specific folder
musicdl download "https://music.youtube.com/playlist?list=PLxxxx" -o ./music

# Parallel — bulk-download a playlist with 8 workers (fast internet → much quicker)
musicdl download "<playlist-url>" -j 8

# Skip cover art and metadata
musicdl download "<url>" --no-thumbnail --no-metadata
```

| Option                 | Default     | Description                                         |
| ---------------------- | ----------- | --------------------------------------------------- |
| `-t`/`--type`          | `audio`     | `audio` or `video`                                  |
| `-a`/`--audio-format`  | `m4a`       | `mp3`, `m4a`, `opus`, `flac`, `wav`, `vorbis`       |
| `-v`/`--video-format`  | `mp4`       | `mp4`, `mkv`, `webm`                                |
| `-q`/`--quality`       | `0`         | Audio: `0` best → `9` worst, or kbps (`192`)        |
| `--max-height`         | uncapped    | Cap video resolution (`1080`, `720`...)             |
| `-o`/`--output`        | `downloads` | Output directory                                    |
| `--thumbnail`          | on          | Embed cover art                                     |
| `--metadata`           | on          | Embed metadata (title, artist...)                   |
| `-j`/`--concurrent`    | `1`         | Parallel workers for playlists (4–8 = much faster)  |

### `sync` — only what's new

Like `download`, but it keeps a **record file** with the IDs already downloaded. Re-run it to fetch only what's new. Pair it with `cron` / Task Scheduler and forget about it.

```bash
# Keep your Liked Music in sync
musicdl sync

# Another playlist, with 8 parallel workers
musicdl sync "https://music.youtube.com/playlist?list=PLxxxx" -o ./music -a mp3 -j 8

# Custom archive file
musicdl sync "<url>" --archive ./state/seen.txt
```

| Option       | Default                              | Description                                |
| ------------ | ------------------------------------ | ------------------------------------------ |
| `--archive`  | `<output>/.musicdl-archive.txt`      | File tracking already-downloaded IDs       |

> Also accepts every `download` flag.

**Maintenance tips:**

| Goal                                      | How                                                              |
| ----------------------------------------- | ---------------------------------------------------------------- |
| Re-download a track you deleted           | Remove its line from `.musicdl-archive.txt`, then `sync` again   |
| Force a full re-sync                      | Delete `.musicdl-archive.txt` and re-run                         |
| Run it daily on Windows                   | `schtasks /create /sc DAILY /tn musicdl-sync /tr "musicdl sync …"` |
| Run it daily on macOS/Linux               | Add `musicdl sync …` to your crontab                             |

### `transcripts` — download subtitles / lyrics

Pulls the available subtitles (manual and auto-generated) from a video or full playlist.

```bash
# A single video
musicdl transcripts "https://youtu.be/<id>"

# Full playlist to a different folder
musicdl transcripts "https://music.youtube.com/playlist?list=LM" -o ./subs

# Spanish only, no auto-generated, VTT format
musicdl transcripts "<url>" -l es --no-auto -f vtt

# Multiple languages (repeat -l)
musicdl transcripts "<url>" -l es -l en -l pt
```

| Option          | Default                              | Description                                  |
| --------------- | ------------------------------------ | -------------------------------------------- |
| `-o`/`--output` | `transcripts`                        | Output directory                             |
| `-l`/`--lang`   | `es`, `en`                           | Languages to try (repeatable)                |
| `--auto`        | on                                   | Include auto-generated subtitles             |
| `-f`/`--format` | `srt`                                | `srt`, `vtt`, `ass`, `lrc`                   |
| `--archive`     | `<output>/.musicdl-archive.txt`      | Re-runnable: skips already-fetched items     |
| `-j`/`--concurrent` | `1`                              | Parallel workers for playlists               |

## Development

```bash
git clone https://github.com/luis-codex/musicdl
cd musicdl
uv sync

# Editable install (changes in source reflect instantly)
uv tool install -e .

# Lint and format
uv run ruff check . --fix
uv run ruff format .
```

## License

MIT
