# musicdl

CLI para trabajar con tus playlists de YouTube Music desde la terminal — listar, descargar (audio o video, en el formato que quieras), sincronizar y bajar transcripciones. Usa las cookies de tu navegador, así que funciona con playlists privadas (incluida tu **Liked Music**).

Construido sobre [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Instalación

Requiere Python ≥ 3.14 (lo provisiona `uv` automáticamente) y [`ffmpeg`](https://ffmpeg.org/) en el `PATH`.

```bash
# Desde GitHub (recomendado)
uv tool install git+https://github.com/luis-codex/musicdl

# O desde un clon local
git clone https://github.com/luis-codex/musicdl
cd musicdl
uv tool install .
```

Una vez instalado, `musicdl` queda disponible globalmente:

```bash
musicdl --help
```

Para actualizar:

```bash
uv tool install git+https://github.com/luis-codex/musicdl --reinstall
```

## Configurar cookies

YouTube Music necesita tus cookies para acceder a playlists privadas (Liked Music, Library, etc.). `musicdl` las lee directamente de tu navegador.

```bash
# Firefox (recomendado en Windows)
musicdl --browser firefox list

# Otros: chrome, brave, edge, opera, vivaldi, safari, chromium...
musicdl --browser chrome list
```

Si usas un fork de Firefox (Zen, Waterfox, LibreWolf) o un perfil custom, indica la ruta:

```bash
musicdl --browser firefox --profile "C:\Users\<tu_usuario>\AppData\Roaming\zen\Profiles\xxxx.Default" list
```

O configúralo una vez vía variables de entorno:

| Variable                    | Default     | Ejemplo                                                                  |
| --------------------------- | ----------- | ------------------------------------------------------------------------ |
| `MUSICDL_BROWSER`           | `firefox`   | `chrome`                                                                 |
| `MUSICDL_BROWSER_PROFILE`   | *(vacío)*   | `C:\Users\luisp\AppData\Roaming\zen\Profiles\xxxx.Default (release)`     |

> ⚠️ **Windows + Chromium (Chrome/Brave/Edge):** desde 2024 esos navegadores usan **Application-Bound Encryption** y `yt-dlp` no puede descifrar sus cookies ([yt-dlp#10927](https://github.com/yt-dlp/yt-dlp/issues/10927)). Usa Firefox/Zen o exporta un `cookies.txt` manualmente.

## Comandos

```bash
musicdl --help
```

### `list` — listar canciones de una playlist

```bash
# Tu Liked Music (default)
musicdl list

# Otra playlist
musicdl list "https://music.youtube.com/playlist?list=PLxxxx"
```

### `download` — descargar audio o video

Descarga un video o playlist completa en el formato elegido. Incluye carátula y metadata embebidos por defecto.

```bash
# Audio M4A (default — sin re-encodear, preserva el AAC original)
musicdl download "https://youtu.be/<id>"

# MP3 a 192 kbps
musicdl download "<url>" -a mp3 -q 192

# FLAC (lossless)
musicdl download "<url>" -a flac

# Video MP4 1080p máx
musicdl download "<url>" -t video -v mp4 --max-height 1080

# Toda una playlist a una carpeta concreta
musicdl download "https://music.youtube.com/playlist?list=PLxxxx" -o ./music

# Sin carátula ni metadata
musicdl download "<url>" --no-thumbnail --no-metadata
```

| Opción                 | Default     | Descripción                                         |
| ---------------------- | ----------- | --------------------------------------------------- |
| `-t`/`--type`          | `audio`     | `audio` o `video`                                   |
| `-a`/`--audio-format`  | `m4a`       | `mp3`, `m4a`, `opus`, `flac`, `wav`, `vorbis`       |
| `-v`/`--video-format`  | `mp4`       | `mp4`, `mkv`, `webm`                                |
| `-q`/`--quality`       | `0`         | Audio: `0` mejor → `9` peor, o kbps (`192`)         |
| `--max-height`         | sin límite  | Cap de resolución de video (`1080`, `720`...)       |
| `-o`/`--output`        | `downloads` | Carpeta de salida                                   |
| `--thumbnail`          | activado    | Embeber carátula                                    |
| `--metadata`           | activado    | Embeber metadata (título, artista...)               |

### `sync` — solo lo nuevo

Como `download`, pero lleva un **archivo de registro** con los IDs ya descargados. Re-ejecutar = solo baja lo nuevo.

```bash
# Mantén tu Liked Music sincronizada
musicdl sync

# Otra playlist
musicdl sync "https://music.youtube.com/playlist?list=PLxxxx" -o ./music -a mp3

# Archivo de registro custom
musicdl sync "<url>" --archive ./state/seen.txt
```

| Opción       | Default                              | Descripción                                |
| ------------ | ------------------------------------ | ------------------------------------------ |
| `--archive`  | `<output>/.musicdl-archive.txt`      | Archivo de IDs ya descargados              |

> Acepta también los flags de `download`.

### `transcripts` — descargar subtítulos / letras

Baja los subtítulos disponibles (manuales y auto-generados) de un video o playlist completa.

```bash
# Un solo video
musicdl transcripts "https://youtu.be/<id>"

# Toda una playlist a otro directorio
musicdl transcripts "https://music.youtube.com/playlist?list=LM" -o ./subs

# Solo español, sin auto-generados, formato VTT
musicdl transcripts "<url>" -l es --no-auto -f vtt

# Varios idiomas (repite -l)
musicdl transcripts "<url>" -l es -l en -l pt
```

| Opción          | Default                              | Descripción                                  |
| --------------- | ------------------------------------ | -------------------------------------------- |
| `-o`/`--output` | `transcripts`                        | Carpeta de salida                            |
| `-l`/`--lang`   | `es`, `en`                           | Idiomas a intentar (repetible)               |
| `--auto`        | activado                             | Incluir subtítulos auto-generados            |
| `-f`/`--format` | `srt`                                | `srt`, `vtt`, `ass`, `lrc`                   |
| `--archive`     | `<output>/.musicdl-archive.txt`      | Re-ejecutable: salta los ya bajados          |

## Desarrollo

```bash
git clone https://github.com/luis-codex/musicdl
cd musicdl
uv sync

# Modo editable (cambios en el código se reflejan al instante)
uv tool install -e .

# Lint y formato
uv run ruff check . --fix
uv run ruff format .
```

## Licencia

MIT
