import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registra las tablas)
from app.config import settings
from app.db import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", str(tmp_path / "media"))
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        c.Session = Session  # para sembrar datos (p. ej. planilleros) en los tests
        yield c
    app.dependency_overrides.clear()


def register(client, email="org@test.com"):
    r = client.post("/api/auth/register", json={"email": email, "name": "Org", "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return register(client)


def make_tournament(client, auth, n_teams, **rules):
    tid = client.post("/api/tournaments", json={"name": "Copa", "rules": rules}, headers=auth).json()["id"]
    ids = []
    for i in range(1, n_teams + 1):
        r = client.post(f"/api/tournaments/{tid}/teams", json={"name": f"Equipo {i}"}, headers=auth)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return tid, ids


def add_scorer(client, auth, tid, match_ids, email="plan@test.com"):
    """Registra un planillero, lo suma al torneo por la API y lo asigna a los partidos."""
    h = register(client, email)
    me = client.get("/api/auth/me", headers=h).json()["id"]
    assert client.post(f"/api/tournaments/{tid}/members", json={"email": email}, headers=auth).status_code == 201
    r = client.post(f"/api/tournaments/{tid}/assignments", json={"user_id": me, "match_ids": match_ids}, headers=auth)
    assert r.status_code == 200, r.text
    return h
