# votingSys — Interfaz Web
Archivos añadidos:
- `static/index.html` — HTML principal de la UI.
- `static/styles.css` — Estilos.
- `static/app.js` — Lógica de cliente y WebSocket.
- `requirements.txt` — Dependencias.
- `start_server.ps1` — Script para arrancar el servidor en Windows PowerShell.

Cómo ejecutar (PowerShell):

```powershell
# instalar dependencias (si no lo hiciste aún)
python -m pip install -r requirements.txt

# arrancar servidor en modo desarrollo
./start_server.ps1
```

La UI estará disponible en `http://localhost:8000/` y el WebSocket en `ws://localhost:8000/ws`.
