"""
Servidor Web de Telemetría e Interfaz Interactiva de Aproximación ILS.

Implementa un servidor HTTP asíncrono y ligero (basado en la biblioteca estándar de Python)
que provee la API REST para simulación dinámica en tiempo real y sirve el panel de control
interactivo web para visualización PFD (Primary Flight Display), instrumentación 3D y telemetría.
"""

import json
import os
import sys
import threading
import traceback
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any

from aero_gnc.config.aircraft_database import AVAILABLE_AIRCRAFT
from aero_gnc.visualization.dashboard_data import simulate_dashboard, validate_dashboard


class FlightDashboardHandler(SimpleHTTPRequestHandler):
    """Manejador HTTP para la API de simulación y recursos estáticos del cliente."""

    def __init__(self, *args, **kwargs):
        # Directorio base para archivos estáticos (HTML/CSS/JS)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        web_dir = os.path.join(project_root, "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self):
        """Maneja solicitudes GET (archivos web y endpoints de diagnóstico)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/aircraft":
            self._send_json({
                "aircraft": [
                    {"id": k, "name": v.name, "description": v.description, "v_ref": v.v_ref, "v_stall": v.v_stall}
                    for k, v in AVAILABLE_AIRCRAFT.items()
                ]
            })
        elif path == "/api/validation":
            self._handle_validation(parsed_url.query)
        elif path == "/api/simulate":
            # Permite ejecutar vía GET con parámetros en query string
            params = urllib.parse.parse_qs(parsed_url.query)
            clean_params = {k: v[0] for k, v in params.items()}
            self._execute_simulation(clean_params)
        else:
            # Servir archivo estático (index.html, styles.css, app.js)
            super().do_GET()

    def do_POST(self):
        """Maneja solicitudes POST (ejecución de simulación con parámetros de entrada)."""
        if self.path == "/api/simulate":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            params = json.loads(body) if body else {}
            self._execute_simulation(params)
        else:
            self.send_error(404, "Endpoint no encontrado")

    def _execute_simulation(self, params: Dict[str, Any]):
        """Ejecuta la corrida con el mismo motor usado por la versión web."""
        try:
            self._send_json(simulate_dashboard(params))
        except Exception as exc:
            traceback.print_exc()
            self._send_json({"status": "error", "message": str(exc)}, status_code=500)

    def _handle_validation(self, query: str):
        """Calcula la validación cuantitativa."""
        try:
            params = urllib.parse.parse_qs(query)
            self._send_json(validate_dashboard(params.get("aircraft_id", ["b737"])[0]))
        except Exception as exc:
            self._send_json({"status": "error", "message": str(exc)}, status_code=500)

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Silencia los logs de cada solicitud para no saturar la salida de terminal."""
        pass


def start_dashboard_server(port: int = 8080, blocking: bool = True) -> HTTPServer:
    """Inicia el servidor web interactivo local."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, FlightDashboardHandler)
    url = f"http://localhost:{port}"
    print(f"\n=======================================================")
    print(f"  PANEL INTERACTIVO AERONÁUTICO ACTIVO (AERO-GNC)")
    print(f"  URL: {url}")
    print(f"  Presione Ctrl+C en la terminal para detener el servidor.")
    print(f"=======================================================\n")

    if blocking:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDeteniendo servidor web...")
            httpd.server_close()
    else:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()

    return httpd
