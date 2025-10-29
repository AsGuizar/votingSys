# Script para arrancar el servidor en modo desarrollo con recarga
# Uso: .\start_server.ps1
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
