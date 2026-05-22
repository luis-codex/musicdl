# musicdl

A command-line tool for working with your YouTube Music playlists — list, download (audio or video, in the format you choose), keep them in sync, and grab transcripts. It reads cookies directly from your browser, so it works with private playlists (including your **Liked Music**).

Built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp).

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

YouTube Music needs your cookies to access private playlists (Liked Music, Library, etc.). `musicdl` reads them straight from your browser.

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

Like `download`, but it keeps a **record file** with the IDs already downloaded. Re-run it to fetch only what's new.

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
