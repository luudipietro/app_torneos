# App de Torneos de Fútbol

- `backend/` — FastAPI + PostgreSQL. `domain/` es el motor puro (fixture, tablas, grupos).
- `frontend/` — PWA React + Vite (pendiente, Fase 2).
- `deploy/` — Nginx, systemd, backups para el VPS de DonWeb (pendiente).

Tests del motor: `cd backend && python -m pytest`

## Backend (desarrollo)
```
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head      # crea torneos.db (SQLite) o usa DATABASE_URL (Postgres)
python -m uvicorn app.main:app --reload   # docs en http://localhost:8000/docs
```

## Frontend (desarrollo)
```
cd frontend
npm install
npm run dev     # http://localhost:5173 (proxy /api -> :8000)
npm run build   # PWA en frontend/dist
```

## Modo offline (cancha sin señal)
El planillero puede marcar presentes, cargar goles/tarjetas, comentar, sacar la foto de la planilla y cerrar el partido sin conexión.
- Cada acción se guarda en una cola local (IndexedDB) y se aplica sobre la copia del partido guardada en el dispositivo.
- Al volver la señal (o cada 15 s) se envía por lotes a `POST /api/sync`. Cada operación tiene un id: reenviar no duplica.
- Si el servidor no puede aplicar algo (p. ej. el organizador cerró el partido), prevalece el servidor y se avisa en la app.
- Los partidos asignados se descargan al abrir «Mis partidos»; abrilos con señal antes de ir a la cancha.
- Necesita conexión: alta de jugadores en la cancha, borrar fotos/comentarios ya enviados, tareas del organizador.
- Tests del cliente: `cd frontend && npm test`.

## Estadísticas y vista pública
- Pestaña **Estadísticas**: goleadores, valla menos vencida, tarjetas, fair play (amarilla 1 pt, roja 3) y suspendidos.
- El organizador activa la **vista pública** desde esa pestaña: link secreto + QR (`/p/<token>`). Muestra posiciones, partidos con goles y tarjetas, llaves y estadísticas, sin login.
  No expone DNI, fotos, comentarios, planillas ni emails. «Generar link nuevo» invalida el anterior; desactivarla lo apaga.
- Fecha y cancha de cada partido se cargan desde la pantalla del partido (organizador).
