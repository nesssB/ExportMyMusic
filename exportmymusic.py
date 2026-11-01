"""ExportMyMusic: descarga en MP3 una lista de canciones usando yt-dlp.

Admite listas de Choosic (.txt, "Canción - Artista"), CSV de Exportify y
texto plano "Artista - Canción".

Uso:
    python exportmymusic.py lista.txt                 # carpeta = nombre del archivo
    python exportmymusic.py playlist.csv -n "Mi Playlist"
    python exportmymusic.py lista.txt --servicio texto
    python exportmymusic.py                           # modo interactivo
"""

import argparse
import csv
import re
import shutil
import sys
from pathlib import Path

import actualizador

SEPARADORES = re.compile(r"\s+[-–—]\s+")
NUMERACION = re.compile(r"^\s*(?:\d+[.)\-:]?|[-*•·])\s+")
CARACTERES_PROHIBIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_NOMBRE = 150  # evita rutas demasiado largas en Windows

SERVICIOS = {
    "choosic": "Choosic (.txt)",
    "exportify": "Exportify (.csv)",
    "texto": "Texto (Artista - Canción)",
}


def ruta_ffmpeg():
    """Usa el ffmpeg del sistema si existe; si no, el que trae imageio-ffmpeg."""
    if shutil.which("ffmpeg"):
        return None
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("No se encontró ffmpeg. Instálalo o ejecuta: pip install imageio-ffmpeg")


def parsear_linea(linea, invertir=False):
    """Devuelve (artista, cancion) o None si la línea está vacía / es un comentario."""
    linea = linea.strip()
    if not linea or linea.startswith("#"):
        return None
    linea = NUMERACION.sub("", linea)
    partes = SEPARADORES.split(linea, maxsplit=1)
    if len(partes) == 1:
        return None, linea
    artista, cancion = partes
    if invertir:
        artista, cancion = cancion, artista
    return artista.strip(), cancion.strip()


def servicio_por_defecto(ruta):
    return "exportify" if Path(ruta).suffix.lower() == ".csv" else "choosic"


def leer_exportify(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        if not {"Track Name", "Artist Name(s)"} <= set(lector.fieldnames or []):
            raise ValueError("El CSV no parece de Exportify: faltan las columnas 'Track Name' y 'Artist Name(s)'.")
        for fila in lector:
            cancion = fila["Track Name"].strip()
            artistas = [a.strip() for a in fila["Artist Name(s)"].split(";") if a.strip()]
            if cancion:
                yield ", ".join(artistas) or None, cancion


def leer_lista(ruta, servicio="choosic"):
    if servicio == "exportify":
        entradas = leer_exportify(ruta)
    else:
        texto = Path(ruta).read_text(encoding="utf-8-sig", errors="replace")
        entradas = (parsear_linea(linea, invertir=servicio == "choosic") for linea in texto.splitlines())

    canciones = []
    vistas = set()
    for resultado in entradas:
        if resultado and resultado not in vistas:
            vistas.add(resultado)
            canciones.append(resultado)
    return canciones


def nombre_seguro(texto):
    return CARACTERES_PROHIBIDOS.sub("", texto)[:MAX_NOMBRE].strip(" .") or "sin_nombre"


def escapar_plantilla(texto):
    # yt-dlp interpreta los % como plantillas de salida
    return texto.replace("%", "%%")


def nombre_archivo(artista, cancion):
    # Exportify puede traer muchos artistas (compositores incluidos); los recortamos para no perder el título
    if artista and len(artista) > 60:
        artista = artista[:60].rsplit(", ", 1)[0] + " y otros"
    return nombre_seguro(f"{artista} - {cancion}" if artista else cancion)


def cargar_ytdlp():
    """Importa yt-dlp tarde, para poder usar la versión descargada por el actualizador."""
    actualizador.preparar()
    try:
        import yt_dlp
    except Exception:  # la versión descargada está rota; usamos la incluida
        actualizador.descartar_local()
        import yt_dlp
    return yt_dlp


def descargar(artista, cancion, carpeta, ffmpeg, calidad):
    """Devuelve ("existe", None) o ("ok", título del vídeo de YouTube elegido)."""
    yt_dlp = cargar_ytdlp()
    nombre = f"{artista} - {cancion}" if artista else cancion
    archivo = nombre_archivo(artista, cancion)
    if (carpeta / f"{archivo}.mp3").exists():
        return "existe", None

    acciones = [(yt_dlp.postprocessor.MetadataParserPP.interpretter,
                 escapar_plantilla(cancion), "(?P<meta_title>.+)")]
    if artista:
        acciones.append((yt_dlp.postprocessor.MetadataParserPP.interpretter,
                         escapar_plantilla(artista), "(?P<meta_artist>.+)"))

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": str(carpeta / f"{escapar_plantilla(archivo)}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "postprocessors": [
            {"key": "MetadataParser", "actions": acciones, "when": "pre_process"},
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": calidad},
            {"key": "FFmpegMetadata"},
        ],
    }
    if ffmpeg:
        opciones["ffmpeg_location"] = ffmpeg

    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(f"ytsearch1:{nombre} audio")
    entradas = info.get("entries") or []
    if not entradas:
        raise RuntimeError("sin resultados en YouTube")
    return "ok", entradas[0].get("title")


def main():
    parser = argparse.ArgumentParser(description="Descarga en MP3 una lista de canciones de Choosic, Exportify o texto plano.")
    parser.add_argument("lista", nargs="?", help="archivo .txt (una canción por línea) o .csv de Exportify")
    parser.add_argument("-n", "--nombre", help="nombre de la carpeta destino (por defecto, el nombre del archivo)")
    parser.add_argument("-s", "--salida", default="Descargas", help="carpeta base donde crear la playlist (por defecto: Descargas)")
    parser.add_argument("-q", "--calidad", default="192", help="bitrate del MP3 en kbps (por defecto: 192)")
    parser.add_argument("--servicio", choices=SERVICIOS,
                        help="formato de la lista (por defecto: exportify si es .csv, choosic si no)")
    args = parser.parse_args()

    if not args.lista:
        args.lista = input("Ruta del archivo .txt o .csv con las canciones: ").strip().strip('"')
        if not args.nombre:
            args.nombre = input("Nombre de la carpeta (Enter = nombre del archivo): ").strip() or None

    if not Path(args.lista).is_file():
        sys.exit(f"No existe el archivo: {args.lista}")

    try:
        canciones = leer_lista(args.lista, args.servicio or servicio_por_defecto(args.lista))
    except ValueError as e:
        sys.exit(str(e))
    if not canciones:
        sys.exit("La lista está vacía.")

    carpeta = Path(args.salida) / nombre_seguro(args.nombre or Path(args.lista).stem)
    carpeta.mkdir(parents=True, exist_ok=True)
    ffmpeg = ruta_ffmpeg()

    print(f"{len(canciones)} canciones -> {carpeta.resolve()}\n")
    fallidas = []
    for i, (artista, cancion) in enumerate(canciones, 1):
        etiqueta = f"{artista} - {cancion}" if artista else cancion
        print(f"[{i}/{len(canciones)}] {etiqueta} ... ", end="", flush=True)
        try:
            estado, video = descargar(artista, cancion, carpeta, ffmpeg, args.calidad)
            print("ya existía" if estado == "existe" else f"OK  [YouTube: {video}]")
        except Exception as e:  # yt-dlp lanza DownloadError y otros; seguimos con la siguiente
            print(f"ERROR ({str(e).splitlines()[0][:100]})")
            fallidas.append(etiqueta)

    print(f"\nTerminado: {len(canciones) - len(fallidas)}/{len(canciones)} descargadas.")
    if fallidas:
        log = carpeta / "fallidas.txt"
        log.write_text("\n".join(fallidas) + "\n", encoding="utf-8")
        print(f"Las que fallaron están en {log}")


if __name__ == "__main__":
    main()
