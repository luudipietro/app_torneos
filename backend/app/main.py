from fastapi import FastAPI

from .routers import auth, draw, knockout, lineup, matches, members, public, sync, stages, tournaments

app = FastAPI(title="App de Torneos", version="0.1.0")
app.include_router(auth.router, prefix="/api")
app.include_router(tournaments.router, prefix="/api")
app.include_router(draw.router, prefix="/api")
app.include_router(stages.router, prefix="/api")
app.include_router(knockout.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(lineup.router, prefix="/api")
app.include_router(members.router, prefix="/api")
app.include_router(sync.router, prefix="/api")
app.include_router(public.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}
