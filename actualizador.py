"""Actualizaciones automáticas.

- La app: compara VERSION con la última release de GitHub y, si hay una nueva,
  descarga el .exe, lo pone en lugar del actual y lo relanza.
- yt-dlp: es Python puro, así que su .whl de PyPI se puede importar directamente
  añadiéndolo a sys.path. Lo guardamos en %LOCALAPPDATA%\\ExportMyMusic\\yt-dlp.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from importlib import metadata
from pathlib import Path

# El workflow de GitHub Actions la sustituye por la del tag (v1.2.3 -> 1.2.3)
VERSION = "1.0.0"
REPO = "nesssB/ExportMyMusic"
NOMBRE_EXE = "ExportMyMusic.exe"
URL_RELEASES = f"https://api.github.com/repos/{REPO}/releases/latest"
URL_PAGINA_RELEASES = f"https://github.com/{REPO}/releases/latest"

CARPETA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ExportMyMusic" / "yt-dlp"
URL_PYPI = "https://pypi.org/pypi/yt-dlp/json"


def _tupla(version):
    return tuple(int(n) for n in re.findall(r"\d+", version))


def _descargar(url, destino, sha256, timeout):
    """Descarga url en destino comprobando el hash; si algo falla no deja el archivo a medias."""
    peticion = urllib.request.Request(url, headers={"User-Agent": "ExportMyMusic"})
    hash_ = hashlib.sha256()
    temporal = destino.with_name(destino.name + ".tmp")
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta, open(temporal, "wb") as f:
            while bloque := respuesta.read(1024 * 256):
                hash_.update(bloque)
                f.write(bloque)
        if sha256 and hash_.hexdigest() != sha256.lower():
            raise ValueError(f"la descarga de {destino.name} no coincide con su hash")
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)


# --- Actualización de la app (GitHub Releases) ---

def buscar_version_app(timeout=10):
    """Devuelve (versión, url del .exe, sha256 o None) si hay una release más nueva, o None."""
    peticion = urllib.request.Request(URL_RELEASES, headers={"Accept": "application/vnd.github+json",
                                                             "User-Agent": "ExportMyMusic"})
    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            datos = json.load(respuesta)
    except urllib.error.HTTPError as e:
        if e.code == 404:  # todavía no hay releases (o el repo es privado)
            return None
        raise
    nueva = datos["tag_name"].lstrip("vV")
    if _tupla(nueva) <= _tupla(VERSION):
        return None
    exe = next((a for a in datos.get("assets", []) if a["name"].lower() == NOMBRE_EXE.lower()), None)
    if not exe:
        return None
    digest = exe.get("digest") or ""
    return nueva, exe["browser_download_url"], digest.removeprefix("sha256:") or None


def instalar_version_app(url, sha256, timeout=30):
    """Sustituye el .exe en ejecución por el nuevo y lo lanza. Después hay que cerrar la app.

    Windows no deja sobrescribir un .exe abierto, pero sí renombrarlo: el actual pasa a
    .old (se borra en el siguiente arranque) y el nuevo ocupa su sitio.
    """
    actual = Path(sys.executable)
    nuevo = actual.with_name(actual.name + ".new")
    viejo = actual.with_name(actual.name + ".old")
    _descargar(url, nuevo, sha256, timeout)

    viejo.unlink(missing_ok=True)
    actual.replace(viejo)
    try:
        nuevo.replace(actual)
    except OSError:
        viejo.replace(actual)
        raise

    # Sin esto, el .exe nuevo de PyInstaller heredaría la carpeta temporal del proceso actual
    entorno = {**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"}
    subprocess.Popen([str(actual)], env=entorno, close_fds=True,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)


def limpiar_version_vieja():
    try:
        Path(sys.executable).with_name(Path(sys.executable).name + ".old").unlink(missing_ok=True)
    except OSError:  # el proceso viejo todavía se está cerrando; ya se borrará
        pass


# --- Actualización de yt-dlp (PyPI) ---

def version_incluida():
    try:
        return metadata.version("yt-dlp")
    except metadata.PackageNotFoundError:
        return None


def wheel_local():
    """Devuelve (ruta, versión) del yt-dlp descargado más reciente, o (None, None)."""
    wheels = sorted(CARPETA.glob("yt_dlp-*.whl"), key=lambda p: _tupla(p.name.split("-")[1]))
    if not wheels:
        return None, None
    return wheels[-1], wheels[-1].name.split("-")[1]


def version_actual():
    candidatas = [v for v in (wheel_local()[1], version_incluida()) if v]
    return max(candidatas, key=_tupla) if candidatas else None


def preparar():
    """Si hay un yt-dlp descargado más nuevo que el incluido, lo pone primero en sys.path."""
    if "yt_dlp" in sys.modules:
        return
    ruta, local = wheel_local()
    if not ruta:
        return
    incluida = version_incluida()
    if (incluida is None or _tupla(local) > _tupla(incluida)) and str(ruta) not in sys.path:
        sys.path.insert(0, str(ruta))


def descartar_local():
    """Quita el yt-dlp descargado de sys.path y de los módulos cargados (por si viene roto)."""
    sys.path[:] = [p for p in sys.path if not str(p).startswith(str(CARPETA))]
    for nombre in [m for m in sys.modules if m == "yt_dlp" or m.startswith("yt_dlp.")]:
        del sys.modules[nombre]


def buscar_actualizacion(timeout=10):
    """Descarga la última versión de yt-dlp si es más nueva. Devuelve esa versión o None."""
    with urllib.request.urlopen(URL_PYPI, timeout=timeout) as respuesta:
        datos = json.load(respuesta)
    nueva = datos["info"]["version"]
    actual = version_actual()
    if actual and _tupla(nueva) <= _tupla(actual):
        return None

    archivo = next(f for f in datos["urls"]
                   if f["packagetype"] == "bdist_wheel" and f["filename"].endswith("-py3-none-any.whl"))
    CARPETA.mkdir(parents=True, exist_ok=True)
    _descargar(archivo["url"], CARPETA / archivo["filename"], archivo["digests"]["sha256"], timeout * 6)
    for viejo in CARPETA.glob("yt_dlp-*.whl"):
        if viejo.name != archivo["filename"]:
            try:
                viejo.unlink()
            except OSError:  # en uso por otra instancia; se borrará la próxima vez
                pass
    return nueva
