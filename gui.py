"""Interfaz gráfica de ExportMyMusic."""

import csv
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import actualizador
from exportmymusic import (SERVICIOS, cargar_ytdlp, descargar, leer_lista, nombre_seguro, ruta_ffmpeg,
                           servicio_por_defecto)

# Con pythonw.exe no hay consola y stdout/stderr son None; yt-dlp necesita poder escribir en ellos
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

EMPAQUETADO = getattr(sys, "frozen", False)
# Empaquetado con PyInstaller, __file__ está en una carpeta temporal; usamos la del .exe
CARPETA_APP = Path(sys.executable).parent if EMPAQUETADO else Path(__file__).parent


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"ExportMyMusic {actualizador.VERSION}")
        self.minsize(560, 440)
        self.eventos = queue.Queue()
        self.carpeta_final = None

        self.var_lista = tk.StringVar()
        self.var_nombre = tk.StringVar()
        self.var_salida = tk.StringVar(value=str(CARPETA_APP / "Descargas"))
        self.var_calidad = tk.StringVar(value="192")
        self.var_servicio = tk.StringVar(value=SERVICIOS["choosic"])

        self.construir()
        self.after(100, self.procesar_eventos)

        # Desde el código se actualiza con git y pip; solo el .exe se actualiza solo
        self.comprobacion_hecha = threading.Event()
        if EMPAQUETADO:
            actualizador.limpiar_version_vieja()
            threading.Thread(target=self.comprobar_actualizaciones, daemon=True).start()
        else:
            self.comprobacion_hecha.set()

    def comprobar_actualizaciones(self):
        """Hilo aparte: primero la app (GitHub), luego yt-dlp (PyPI). Sin internet, se ignora."""
        self.eventos.put(("estado", "Buscando actualizaciones…"))
        try:
            nueva_app = actualizador.buscar_version_app()
            if nueva_app:
                self.eventos.put(("app_nueva", *nueva_app))
        except Exception:
            pass
        try:
            nueva = actualizador.buscar_actualizacion()
            self.eventos.put(("estado", f"yt-dlp actualizado a {nueva}" if nueva else ""))
        except Exception:
            self.eventos.put(("estado", ""))
        finally:
            self.comprobacion_hecha.set()

    def ofrecer_actualizacion(self, version, url, sha256):
        if not messagebox.askyesno("ExportMyMusic",
                                   f"Hay una nueva versión de ExportMyMusic ({version}).\n"
                                   f"Tienes la {actualizador.VERSION}.\n\n¿Actualizar ahora?"):
            return
        self.btn_descargar.configure(state="disabled")
        self.lbl_estado.configure(text=f"Descargando la versión {version}…")

        def instalar():
            try:
                actualizador.instalar_version_app(url, sha256)
                self.eventos.put(("reiniciar",))
            except Exception as e:
                self.eventos.put(("error_actualizacion", str(e)))

        threading.Thread(target=instalar, daemon=True).start()

    def construir(self):
        marco = ttk.Frame(self, padding=12)
        marco.pack(fill="both", expand=True)
        marco.columnconfigure(1, weight=1)

        ttk.Label(marco, text="Lista:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(marco, textvariable=self.var_lista).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(marco, text="Examinar…", command=self.elegir_lista).grid(row=0, column=2)

        ttk.Label(marco, text="Nombre carpeta:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(marco, textvariable=self.var_nombre).grid(row=1, column=1, columnspan=2, sticky="ew", padx=(6, 0))

        ttk.Label(marco, text="Guardar en:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(marco, textvariable=self.var_salida).grid(row=2, column=1, sticky="ew", padx=6)
        ttk.Button(marco, text="Examinar…", command=self.elegir_salida).grid(row=2, column=2)

        opciones = ttk.Frame(marco)
        opciones.grid(row=3, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Label(opciones, text="Servicio:").pack(side="left")
        ttk.Combobox(opciones, textvariable=self.var_servicio, values=list(SERVICIOS.values()),
                     width=24, state="readonly").pack(side="left", padx=(6, 18))
        ttk.Label(opciones, text="Calidad (kbps):").pack(side="left")
        ttk.Combobox(opciones, textvariable=self.var_calidad, values=["128", "192", "256", "320"],
                     width=5, state="readonly").pack(side="left", padx=6)

        botones = ttk.Frame(marco)
        botones.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        self.btn_descargar = ttk.Button(botones, text="Descargar", command=self.iniciar)
        self.btn_descargar.pack(side="left")
        self.btn_abrir = ttk.Button(botones, text="Abrir carpeta", command=self.abrir_carpeta, state="disabled")
        self.btn_abrir.pack(side="left", padx=6)
        self.lbl_estado = ttk.Label(botones, text="")
        self.lbl_estado.pack(side="right")

        self.progreso = ttk.Progressbar(marco, mode="determinate")
        self.progreso.grid(row=5, column=0, columnspan=3, sticky="ew", pady=4)

        registro = ttk.Frame(marco)
        registro.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=(4, 0))
        marco.rowconfigure(6, weight=1)
        self.txt_log = tk.Text(registro, height=12, state="disabled", wrap="none")
        barra = ttk.Scrollbar(registro, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=barra.set)
        self.txt_log.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.txt_log.tag_configure("ok", foreground="#1a7f37")
        self.txt_log.tag_configure("error", foreground="#cf222e")
        self.txt_log.tag_configure("info", foreground="#57606a")

    def elegir_lista(self):
        ruta = filedialog.askopenfilename(title="Elige la lista de canciones",
                                          filetypes=[("Listas", "*.txt *.csv"), ("Texto (Choosic)", "*.txt"),
                                                     ("CSV (Exportify)", "*.csv"), ("Todos", "*.*")])
        if ruta:
            self.var_lista.set(ruta)
            self.var_servicio.set(SERVICIOS[servicio_por_defecto(ruta)])
            if not self.var_nombre.get():
                self.var_nombre.set(Path(ruta).stem)

    def elegir_salida(self):
        ruta = filedialog.askdirectory(title="Carpeta donde guardar", initialdir=self.var_salida.get())
        if ruta:
            self.var_salida.set(ruta)

    def abrir_carpeta(self):
        if self.carpeta_final and self.carpeta_final.exists():
            os.startfile(self.carpeta_final)

    def log(self, texto, etiqueta=None):
        self.txt_log.configure(state="normal")
        self.txt_log.insert("end", texto, etiqueta)
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def iniciar(self):
        lista = self.var_lista.get().strip().strip('"')
        if not Path(lista).is_file():
            messagebox.showerror("ExportMyMusic", "Elige un archivo .txt o .csv válido.")
            return
        servicio = next(clave for clave, texto in SERVICIOS.items() if texto == self.var_servicio.get())
        try:
            canciones = leer_lista(lista, servicio)
        except (ValueError, UnicodeDecodeError, csv.Error) as e:
            messagebox.showerror("ExportMyMusic", f"No se pudo leer la lista:\n{e}")
            return
        if not canciones:
            messagebox.showerror("ExportMyMusic", "La lista está vacía.")
            return

        nombre = self.var_nombre.get().strip() or Path(lista).stem
        self.carpeta_final = Path(self.var_salida.get()) / nombre_seguro(nombre)
        self.carpeta_final.mkdir(parents=True, exist_ok=True)

        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")
        self.log(f"{len(canciones)} canciones -> {self.carpeta_final.resolve()}\n\n", "info")
        self.progreso.configure(maximum=len(canciones), value=0)
        self.btn_descargar.configure(state="disabled")
        self.btn_abrir.configure(state="normal")

        hilo = threading.Thread(target=self.trabajar, daemon=True,
                                args=(canciones, self.carpeta_final, self.var_calidad.get()))
        hilo.start()

    def trabajar(self, canciones, carpeta, calidad):
        """Se ejecuta en un hilo aparte; comunica con la interfaz solo a través de la cola."""
        self.comprobacion_hecha.wait(timeout=60)
        self.eventos.put(("info", f"yt-dlp {cargar_ytdlp().version.__version__}\n\n"))
        ffmpeg = ruta_ffmpeg()
        fallidas = []
        for i, (artista, cancion) in enumerate(canciones, 1):
            etiqueta = f"{artista} - {cancion}" if artista else cancion
            self.eventos.put(("inicio", i, len(canciones), etiqueta))
            try:
                estado, video = descargar(artista, cancion, carpeta, ffmpeg, calidad)
                self.eventos.put(("ok", "ya existía" if estado == "existe" else "OK", video))
            except Exception as e:  # seguimos con la siguiente
                self.eventos.put(("error", str(e).splitlines()[0][:100]))
                fallidas.append(etiqueta)
        if fallidas:
            (carpeta / "fallidas.txt").write_text("\n".join(fallidas) + "\n", encoding="utf-8")
        self.eventos.put(("fin", len(canciones), len(fallidas)))

    def procesar_eventos(self):
        while not self.eventos.empty():
            evento = self.eventos.get()
            tipo = evento[0]
            if tipo == "inicio":
                _, i, total, etiqueta = evento
                self.lbl_estado.configure(text=f"{i}/{total}")
                self.log(f"[{i}/{total}] {etiqueta} ... ")
            elif tipo == "estado":
                if self.btn_descargar.instate(["!disabled"]):  # no pisar "Descargando la versión…"
                    self.lbl_estado.configure(text=evento[1])
            elif tipo == "app_nueva":
                self.ofrecer_actualizacion(*evento[1:])
            elif tipo == "reiniciar":
                self.destroy()
                return
            elif tipo == "error_actualizacion":
                self.btn_descargar.configure(state="normal")
                self.lbl_estado.configure(text="")
                if messagebox.askyesno("ExportMyMusic", f"No se pudo actualizar:\n{evento[1]}\n\n"
                                                        "¿Abrir la página de descargas para bajarla a mano?"):
                    webbrowser.open(actualizador.URL_PAGINA_RELEASES)
            elif tipo == "info":
                self.log(evento[1], "info")
            elif tipo == "ok":
                self.log(evento[1], "ok")
                self.log(f"  [YouTube: {evento[2]}]\n" if evento[2] else "\n", "info")
                self.progreso.step(1)
            elif tipo == "error":
                self.log(f"ERROR ({evento[1]})\n", "error")
                self.progreso.step(1)
            elif tipo == "fin":
                _, total, n_fallidas = evento
                self.progreso.configure(value=total)
                resumen = f"Terminado: {total - n_fallidas}/{total} descargadas."
                if n_fallidas:
                    resumen += " Las que fallaron están en fallidas.txt"
                self.log(f"\n{resumen}\n", "info")
                self.lbl_estado.configure(text="Terminado")
                self.btn_descargar.configure(state="normal")
        self.after(100, self.procesar_eventos)


if __name__ == "__main__":
    App().mainloop()
