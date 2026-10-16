# App de Torneos de Fútbol — contexto del proyecto

Leé este archivo al retomar el trabajo en otra PC. Idioma de la app y de la conversación: **español (Argentina)**.

## Objetivo
App para organizar torneos de fútbol (hasta 64 equipos): grupos y fixture automáticos, equipos y jugadores, resultados con goleadores, tarjetas, foto de planilla y comentarios, control de **buena fe** antes de cada partido. Se usa en PC (web) y en celulares/tablets (misma PWA instalable). Debe funcionar **sin internet en la cancha**.

## Decisiones tomadas
- Usuarios con roles por torneo: **admin** (organizador) y **scorer** (planillero/veedor, solo ve/carga sus partidos asignados). Público: solo lectura por link.
- Buena fe: el veedor marca presentes viendo foto + DNI; se bloquean suspendidos y jugadores no habilitados; se permite alta de jugador en la cancha (configurable).
- Stack: **PWA React + TypeScript + Vite + Tailwind** (no Next.js) y **backend FastAPI (Python) + SQLAlchemy + Alembic**. Producción prevista: **VPS de DonWeb** (Nginx + systemd + PostgreSQL + HTTPS + backups). Desarrollo: SQLite.
- Offline: cola de operaciones en IndexedDB + `POST /api/sync` idempotente; ante conflicto gana el servidor.
- **Despliegue: todavía NO se hizo** (el usuario pidió dejarlo para después). `deploy/` está vacío.

## Estructura
```
backend/
  domain/      motor puro sin DB: fixture.py (round-robin), standings.py (tabla y desempates),
               groups.py (layouts y sorteo), discipline.py (suspensiones), knockout.py (llaves y byes),
               qualification.py (clasificación a copas, mejores N, evitar mismo grupo)
  app/         models.py, schemas.py, security.py (JWT+argon2), deps.py, config.py, db.py,
               bracket.py (avance de ganadores), discipline.py, stats.py, media.py (imágenes)
    routers/   auth, tournaments (+equipos/jugadores/fotos/stats), stages, knockout, matches,
               lineup (buena fe), members (invitaciones/asignaciones/fecha-cancha), sync, public
  alembic/     migraciones (SQLite: usar índices únicos, no ALTER de constraints)
  tests/       pytest (302 tests)
frontend/src/
  api.ts       cliente tipado (+ publicApi sin auth)
  offline/     idb.ts, queue.ts (cola/flush), apply.ts (aplica pendientes sobre la copia), hooks.ts,
               SyncBanner.tsx, image.ts, cache.ts, offline.test.ts (vitest)
  pages/       Login, Tournaments, TournamentPage (tabs), Teams, Groups, Bracket, MatchPage,
               LineupPage, Sanctions, Stats, Staff, MyMatches, PublicPage
  components/  StatsView.tsx
deploy/        vacío (pendiente)
.claude/launch.json   servidores de dev: api (:8000), web (:5173), web-preview (:4173, build PWA)
```

## Funcionalidades hechas
1. Auth (registro/login JWT), torneos, equipos (máx. 64), jugadores (DNI único por torneo, foto, habilitado).
2. Sorteo de grupos con cabezas de serie, fixture round-robin (ida/vuelta), tablas con desempates configurables.
3. Partido: goles/penales/en contra, amarillas/rojas/doble amarilla (el marcador se calcula de los goles), foto de planilla, comentarios, cierre/reapertura (solo admin edita partido cerrado), fecha y cancha.
4. Buena fe + suspensiones automáticas (reglas en `tournament.rules`: `yellows_for_suspension`=3, `yellow_suspension_matches`, `red_suspension_matches`, `require_lineup`, `allow_onsite_players`, `win/draw/loss`, `tiebreakers`).
5. Equipo de trabajo: invitar por email (si no tiene cuenta queda pendiente y entra al registrarse), asignar partidos uno a uno o en bloque, «Mis partidos» para el planillero. **La app no envía mails.**
6. Llaves: byes, 3er puesto, penales, clasificación desde grupos (top N + mejores N), Copa de Oro/Plata, evitar cruces del mismo grupo, avance automático de ganadores.
7. Offline completo para el planillero (buena fe, eventos, comentarios, foto, cierre). Alta de jugador en cancha y borrar fotos/comentarios ya enviados requieren conexión.
8. Estadísticas (goleadores, valla menos vencida, tarjetas, fair play 1/3 pts, suspendidos) y **vista pública** `/p/<token>` con QR (no expone DNI, fotos, comentarios ni emails).

## Cómo retomar en otra PC
Requisitos: Python 3.12+ y Node 20+ (se usó Python 3.14, Node 24).
```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m alembic upgrade head        # crea backend/torneos.db (SQLite)
python -m pytest -q                   # 302 tests
python -m uvicorn app.main:app --reload   # docs en :8000/docs
cd ../frontend
npm install
npm test                              # vitest (15 tests)
npm run dev                           # :5173, proxy /api -> :8000
npm run build                         # PWA en dist/ (probar offline con `npm run preview`, :4173)
```
Variables (`backend/.env`, ver `.env.example`): `DATABASE_URL` (Postgres en prod), `SECRET_KEY` (**cambiar**; el default es corto y genera warnings), `MEDIA_DIR`.
`torneos.db`, `media/`, `dist/`, `node_modules/` no se versionan: en la PC nueva se parte de base vacía.

## Convenciones y trampas aprendidas
- Mantener el motor de torneos en `backend/domain` puro y testeable; la lógica de endpoints reutiliza funciones (p. ej. `sync.py` llama a los endpoints de matches/lineup).
- Planilleros: `_match()` en `routers/matches.py` devuelve 403 si no está asignado; usar siempre `_match` + `_writable` para escribir sobre partidos.
- Migraciones: tras cambiar `models.py` correr `alembic revision --autogenerate` y `alembic check`; en SQLite evitar `unique=True` sin índice (usar `unique=True, index=True`).
- Antes de borrar `torneos.db` en dev, parar el servidor (Windows lo bloquea).
- Datos de prueba en el navegador: registrarse y cargar por `fetch('/api/...')` desde la consola; limpiar `localStorage` (`token`, `me`) al cambiar de usuario.
- Cada vez que se agrega algo: tests de backend (pytest) y, si toca la cola, vitest; verificar en el navegador con los servidores de `.claude/launch.json`.

## Pendiente / ideas
- **Despliegue en DonWeb** (Nginx, systemd/uvicorn, PostgreSQL, Let's Encrypt, backups `pg_dump`, `SECRET_KEY` real, CORS/HTTPS, límites de subida). Verificar RAM/CPU/SO del VPS primero.
- Revisión general de seguridad, rendimiento y UX antes de desplegar (rate limit en login, refresh tokens, política de contraseñas).
- Probar en celular real: instalación PWA, cámara, offline real.
- Importación Excel/CSV de planteles, exportar fixture/tablas a PDF/Excel, notificaciones (push/WhatsApp), escudos de equipos (subida), llaves con ida y vuelta, formato suizo.
- Probar la UI con 64 equipos (solo está probado en el motor y en la API).
