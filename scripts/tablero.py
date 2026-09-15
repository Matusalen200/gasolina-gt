"""Abre el tablero de Gasolina GT en tu navegador.

Levanta un servidor chiquito en tu propia PC (nadie más lo ve) y abre la página.
Hace falta porque el navegador no deja leer los datos si la página se abre como archivo suelto.

Doble clic en «Gasolina GT.bat», o:
    .venv\\Scripts\\python.exe scripts\\tablero.py
"""
from __future__ import annotations

import http.server
import socket
import socketserver
import sys
import threading
import webbrowser
from functools import partial
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PUERTO_PREFERIDO = 8765


def _puerto_libre(preferido: int) -> int:
    for puerto in (preferido, 0):
        try:
            with socket.socket() as s:
                s.bind(("127.0.0.1", puerto))
                return s.getsockname()[1]
        except OSError:
            continue
    return preferido


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # sin ruido en la ventana
        pass


def main() -> int:
    puerto = _puerto_libre(PUERTO_PREFERIDO)
    handler = partial(_Silencioso, directory=str(RAIZ))
    socketserver.TCPServer.allow_reuse_address = True
    try:
        servidor = socketserver.TCPServer(("127.0.0.1", puerto), handler)
    except OSError as e:
        print(f"No pude abrir el tablero: {e}")
        return 1
    url = f"http://127.0.0.1:{puerto}/web/"
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(f"Tablero abierto en: {url}")
    print("Deja esta ventana abierta mientras lo miras. Ciérrala para terminar.")
    webbrowser.open(url)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    servidor.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
