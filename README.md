# ExportMyMusic

**English** · [Español](#español)

Turn a playlist into a folder of MP3 files. Give ExportMyMusic a song list from
[Choosic](https://www.choosic.com/) or a CSV from [Exportify](https://exportify.net/),
and it searches YouTube for each track, downloads it with
[yt-dlp](https://github.com/yt-dlp/yt-dlp) and saves it as a tagged MP3 in a folder
named after your playlist.

## Features

- Simple desktop window: pick your list, name the folder, click **Download**
- Supports Choosic `.txt` lists, Exportify `.csv` exports and plain `Artist - Song` text files
- MP3 output at 128, 192, 256 or 320 kbps with artist and title tags
- Files named `Artist - Song.mp3`
- Re-running a list skips songs you already have
- Songs that fail are saved to `fallidas.txt` so you can retry them
- The log shows which YouTube video was picked for each song, so mismatches are easy to spot
- ffmpeg is bundled, so there's nothing extra to install
- Updates itself: new app versions from GitHub Releases and the latest yt-dlp from PyPI

## Download (Windows)

1. Go to the [Releases](../../releases) page and download `ExportMyMusic.exe`.
2. Double-click it. No Python or other installs needed.

> **Windows SmartScreen** may warn that the app is unrecognized because it isn't signed.
> Click **More info → Run anyway**. Some antivirus programs also flag apps built with
> PyInstaller as a false positive.

### Automatic updates

Every time it starts, the `.exe` checks for updates in the background:

- **App**: if there's a newer release on GitHub, it asks whether to update. If you accept,
  it downloads the new `.exe`, verifies its SHA-256, replaces itself and restarts.
- **yt-dlp**: if PyPI has a newer version, it's downloaded silently to
  `%LOCALAPPDATA%\ExportMyMusic` and used from then on. This keeps downloads working when
  YouTube changes, even without a new app release.

Without an internet connection the check is skipped. If an update fails, the app keeps
using the version it already has.

## How to use

1. Get your list:
   - **Choosic**: copy the generated playlist into a `.txt` file, one song per line.
   - **Exportify**: export your Spotify playlist as CSV.
2. Open ExportMyMusic and click **Browse…** next to *Lista* to pick the file.
   The service is detected from the file extension (`.csv` → Exportify, `.txt` → Choosic).
3. Optionally change the folder name, destination and quality.
4. Click **Descargar** and wait. **Abrir carpeta** opens the folder with your MP3s.

By default, songs are saved in a `Descargas` folder next to the app.

> The interface is in Spanish: *Lista* = list, *Nombre carpeta* = folder name,
> *Guardar en* = save to, *Servicio* = service, *Calidad* = quality,
> *Descargar* = download, *Abrir carpeta* = open folder.

### Supported list formats

| Service | File | Line format |
|---|---|---|
| Choosic | `.txt` | `Song - Artist` |
| Exportify | `.csv` | Uses the `Track Name` and `Artist Name(s)` columns |
| Plain text | `.txt` | `Artist - Song` |

For text files, empty lines, lines starting with `#`, numbering (`1.`, `2)`) and bullets
are ignored, and duplicates are removed. `-`, `–` and `—` all work as separators.

## Run from source

Requires Python 3.10 or newer.

```bash
git clone https://github.com/nesssB/ExportMyMusic.git
cd ExportMyMusic
python -m venv .venv
.venv\Scripts\activate        # on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Graphical interface:

```bash
python gui.py
```

Command line:

```bash
python exportmymusic.py playlist.csv -n "My Playlist"
python exportmymusic.py list.txt --servicio texto -q 320
python exportmymusic.py               # interactive mode
```

| Option | Description |
|---|---|
| `-n`, `--nombre` | Folder name (defaults to the file name) |
| `-s`, `--salida` | Base folder (defaults to `Descargas`) |
| `-q`, `--calidad` | MP3 bitrate in kbps (defaults to `192`) |
| `--servicio` | `choosic`, `exportify` or `texto` (detected from the extension if omitted) |

On Windows you can also double-click `ExportMyMusic.bat` to open the interface.

### Build the .exe

```bash
pip install pyinstaller
build.bat
```

The result is `dist\ExportMyMusic.exe`.

### Publish a release

Push a version tag and GitHub Actions builds the `.exe` and publishes it to Releases.
Installed copies will offer to update on their next start.

```bash
git tag v1.1.0
git push origin v1.1.0
```

The version shown in the app comes from the tag, so there's no need to edit it in the code.

## Troubleshooting

- **Downloads suddenly stop working.** YouTube changes often and older yt-dlp versions
  break. The `.exe` updates yt-dlp on its own, so restart it with an internet connection.
  From source, run `pip install -U yt-dlp`.
- **Wrong version of a song (live, remix, music video).** The app takes the first YouTube
  result. Check the `[YouTube: ...]` note in the log, delete the wrong file, make the line
  in your list more specific and run it again. Songs you already have are skipped.

## Disclaimer

This project is for personal use only. Downloading content from YouTube may go against
its Terms of Service and copyright law in your country. You are responsible for how you
use this tool. Please support the artists you listen to.

---

## Español

[English](#exportmymusic) · **Español**

Convierte una playlist en una carpeta de MP3. Dale a ExportMyMusic una lista de canciones
de [Choosic](https://www.choosic.com/) o un CSV de [Exportify](https://exportify.net/),
y busca cada canción en YouTube, la descarga con
[yt-dlp](https://github.com/yt-dlp/yt-dlp) y la guarda como MP3 etiquetado en una
carpeta con el nombre de tu playlist.

### Características

- Ventana sencilla: eliges la lista, pones nombre a la carpeta y pulsas **Descargar**
- Admite listas `.txt` de Choosic, `.csv` de Exportify y texto `Artista - Canción`
- MP3 a 128, 192, 256 o 320 kbps con etiquetas de artista y título
- Archivos con el nombre `Artista - Canción.mp3`
- Si vuelves a ejecutar una lista, se salta las canciones que ya tienes
- Las que fallan se guardan en `fallidas.txt` para reintentarlas
- El registro muestra qué vídeo de YouTube se eligió para cada canción
- Incluye ffmpeg, no hay que instalar nada más
- Se actualiza sola: nuevas versiones de la app desde GitHub Releases y la última versión de yt-dlp desde PyPI

### Descarga (Windows)

1. Ve a [Releases](../../releases) y descarga `ExportMyMusic.exe`.
2. Ábrelo con doble clic. No necesitas Python ni nada más.

> **Windows SmartScreen** puede avisar de que es una app desconocida porque no está firmada.
> Pulsa **Más información → Ejecutar de todas formas**. Algunos antivirus también dan falsos
> positivos con apps hechas con PyInstaller.

#### Actualizaciones automáticas

Cada vez que se abre, el `.exe` busca actualizaciones en segundo plano:

- **App**: si hay una release más nueva en GitHub, te pregunta si quieres actualizar. Si
  aceptas, descarga el nuevo `.exe`, comprueba su SHA-256, se sustituye a sí misma y se reinicia.
- **yt-dlp**: si PyPI tiene una versión más nueva, se descarga en silencio en
  `%LOCALAPPDATA%\ExportMyMusic` y se usa a partir de ese momento. Así las descargas siguen
  funcionando cuando YouTube cambia, aunque no haya una versión nueva de la app.

Sin conexión a internet no se comprueba nada. Si una actualización falla, la app sigue
usando la versión que ya tenía.

### Cómo se usa

1. Consigue tu lista:
   - **Choosic**: copia la playlist generada en un `.txt`, una canción por línea.
   - **Exportify**: exporta tu playlist de Spotify como CSV.
2. Abre ExportMyMusic y pulsa **Examinar…** junto a *Lista* para elegir el archivo.
   El servicio se detecta por la extensión (`.csv` → Exportify, `.txt` → Choosic).
3. Si quieres, cambia el nombre de la carpeta, el destino y la calidad.
4. Pulsa **Descargar** y espera. **Abrir carpeta** abre la carpeta con tus MP3.

Por defecto, las canciones se guardan en una carpeta `Descargas` junto a la app.

#### Formatos de lista

| Servicio | Archivo | Formato de línea |
|---|---|---|
| Choosic | `.txt` | `Canción - Artista` |
| Exportify | `.csv` | Usa las columnas `Track Name` y `Artist Name(s)` |
| Texto | `.txt` | `Artista - Canción` |

En los archivos de texto se ignoran las líneas vacías, las que empiezan por `#`, la
numeración (`1.`, `2)`) y las viñetas, y se quitan los duplicados. Sirven como separador
`-`, `–` y `—`.

### Ejecutar desde el código

Necesitas Python 3.10 o posterior.

```bash
git clone https://github.com/nesssB/ExportMyMusic.git
cd ExportMyMusic
python -m venv .venv
.venv\Scripts\activate        # en macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Interfaz gráfica: `python gui.py`

Línea de comandos:

```bash
python exportmymusic.py playlist.csv -n "Mi Playlist"
python exportmymusic.py lista.txt --servicio texto -q 320
python exportmymusic.py               # modo interactivo
```

| Opción | Descripción |
|---|---|
| `-n`, `--nombre` | Nombre de la carpeta (por defecto, el del archivo) |
| `-s`, `--salida` | Carpeta base (por defecto, `Descargas`) |
| `-q`, `--calidad` | Bitrate del MP3 en kbps (por defecto, `192`) |
| `--servicio` | `choosic`, `exportify` o `texto` (si no se indica, se detecta por la extensión) |

En Windows también puedes abrir la interfaz con doble clic en `ExportMyMusic.bat`.

#### Generar el .exe

```bash
pip install pyinstaller
build.bat
```

El resultado queda en `dist\ExportMyMusic.exe`.

#### Publicar una versión

Sube un tag de versión y GitHub Actions compila el `.exe` y lo publica en Releases.
Las copias instaladas ofrecerán actualizarse la próxima vez que se abran.

```bash
git tag v1.1.0
git push origin v1.1.0
```

La versión que muestra la app sale del tag, así que no hace falta cambiarla en el código.

### Problemas frecuentes

- **De repente deja de descargar.** YouTube cambia a menudo y las versiones antiguas de
  yt-dlp dejan de funcionar. El `.exe` actualiza yt-dlp solo, así que basta con volver a
  abrirlo con conexión a internet. Desde el código, ejecuta `pip install -U yt-dlp`.
- **Se baja otra versión de la canción (directo, remix, videoclip).** La app coge el primer
  resultado de YouTube. Mira la nota `[YouTube: ...]` en el registro, borra el archivo,
  pon esa línea de la lista más específica y vuelve a ejecutarla. Las que ya tienes se saltan.

### Aviso

Este proyecto es solo para uso personal. Descargar contenido de YouTube puede ir contra
sus condiciones de uso y contra las leyes de derechos de autor de tu país. Eres responsable del uso que hagas de esta herramienta. Apoya a los artistas que escuchas.
