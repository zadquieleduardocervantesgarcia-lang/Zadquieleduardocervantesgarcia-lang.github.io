"""Servidor local de la interfaz (HUD): sirve hud/index.html y le manda a la página, en vivo,
lo que JARVIS está haciendo (escuchando, pensando, hablando y el volumen de su voz).

Solo escucha en tu propia Mac (127.0.0.1): nadie más en la red puede abrirla.
"""

import json
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = 8777
CARPETA_HUD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hud")


class Hud:
    def __init__(self, puerto=PUERTO):
        self.puerto = puerto
        self.clientes = []
        self.candado = threading.Lock()
        # Lo que la página pide: ("voz", None) para escuchar o ("texto", "...") si escribiste.
        self.ordenes = queue.Queue()
        self.config = {}

    @property
    def url(self):
        return f"http://localhost:{self.puerto}"

    def enviar(self, **evento):
        """Manda un evento a todas las páginas abiertas."""
        datos = json.dumps(evento, ensure_ascii=False)
        with self.candado:
            for cliente in self.clientes:
                cliente.put(datos)

    def iniciar(self):
        hud = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass  # sin mensajes en la Terminal por cada petición

            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    with open(os.path.join(CARPETA_HUD, "index.html"), "rb") as f:
                        contenido = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(contenido)
                elif self.path == "/eventos":
                    self._eventos()
                else:
                    self.send_error(404)

            def _eventos(self):
                """Conexión abierta (Server-Sent Events) por donde viajan los eventos a la página."""
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                cola = queue.Queue()
                cola.put(json.dumps({"tipo": "config", **hud.config}, ensure_ascii=False))
                with hud.candado:
                    hud.clientes.append(cola)
                try:
                    while True:
                        try:
                            self.wfile.write(f"data: {cola.get(timeout=15)}\n\n".encode())
                        except queue.Empty:
                            self.wfile.write(b": sigo aqui\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    with hud.candado:
                        hud.clientes.remove(cola)

            def do_POST(self):
                largo = int(self.headers.get("Content-Length") or 0)
                cuerpo = json.loads(self.rfile.read(largo) or b"{}")
                if self.path == "/hablar":
                    hud.ordenes.put(("voz", None))
                elif self.path == "/escribir" and cuerpo.get("texto", "").strip():
                    hud.ordenes.put(("texto", cuerpo["texto"].strip()))
                else:
                    self.send_error(400)
                    return
                self.send_response(204)
                self.end_headers()

        servidor = ThreadingHTTPServer(("127.0.0.1", self.puerto), Manejador)
        servidor.daemon_threads = True
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
