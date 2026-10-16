"""Estadísticas del torneo a partir de los partidos y sus incidencias."""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .discipline import tournament_suspensions

SCORER_LIMIT = 30
CARD_LIMIT = 100
RED_POINTS = 3  # peso de una roja en el fair play (la amarilla pesa 1)


def _ranked(rows: list, key) -> list[int]:
    """Posiciones con empates: 1, 2, 2, 4..."""
    ranks, last = [], None
    for i, r in enumerate(rows, 1):
        k = key(r)
        ranks.append(ranks[-1] if k == last else i)
        last = k
    return ranks


def compute_stats(db: Session, t: models.Tournament) -> schemas.StatsOut:
    teams = {x.id: x.name for x in db.scalars(select(models.Team).where(models.Team.tournament_id == t.id))}
    players = {p.id: p for p in db.scalars(select(models.Player).where(models.Player.tournament_id == t.id))}
    matches = db.scalars(select(models.Match).where(models.Match.tournament_id == t.id)).all()
    events = db.scalars(
        select(models.MatchEvent).join(models.Match, models.Match.id == models.MatchEvent.match_id)
        .where(models.Match.tournament_id == t.id)
    ).all()

    # --- goleadores (el gol en contra no suma al jugador)
    goals: dict[int, int] = defaultdict(int)
    pens: dict[int, int] = defaultdict(int)
    for e in events:
        if e.type in ("goal", "penalty_goal"):
            goals[e.player_id] += 1
            pens[e.player_id] += e.type == "penalty_goal"
    order = sorted(goals, key=lambda pid: (-goals[pid], players[pid].name))
    ranks = _ranked(order, lambda pid: goals[pid])
    scorers = [
        schemas.ScorerRow(
            rank=r, player_id=pid, name=players[pid].name, team_id=players[pid].team_id,
            team_name=teams[players[pid].team_id], goals=goals[pid], penalties=pens[pid])
        for pid, r in zip(order, ranks)
    ][:SCORER_LIMIT]

    # --- tarjetas (la doble amarilla cuenta como roja, no suma a las amarillas)
    yellow: dict[int, int] = defaultdict(int)
    red: dict[int, int] = defaultdict(int)
    for e in events:
        if e.type == "yellow":
            yellow[e.player_id] += 1
        elif e.type in ("red", "second_yellow"):
            red[e.player_id] += 1
    carded = sorted(set(yellow) | set(red), key=lambda pid: (-red[pid], -yellow[pid], players[pid].name))
    cards = [
        schemas.CardRow(
            player_id=pid, name=players[pid].name, team_id=players[pid].team_id,
            team_name=teams[players[pid].team_id], yellow=yellow[pid], red=red[pid])
        for pid in carded
    ][:CARD_LIMIT]

    # --- valla menos vencida y fair play por equipo
    played: dict[int, int] = defaultdict(int)
    against: dict[int, int] = defaultdict(int)
    clean: dict[int, int] = defaultdict(int)
    total_goals = 0
    finished = [m for m in matches if m.status == "finished" and m.home_goals is not None and m.away_goals is not None]
    for m in finished:
        total_goals += m.home_goals + m.away_goals
        for team, conceded in ((m.home_team_id, m.away_goals), (m.away_team_id, m.home_goals)):
            if team is None:
                continue
            played[team] += 1
            against[team] += conceded
            clean[team] += conceded == 0
    avg = lambda tid: against[tid] / played[tid]
    order_t = sorted(played, key=lambda tid: (avg(tid), -clean[tid], teams[tid]))
    dranks = _ranked(order_t, lambda tid: (round(avg(tid), 6), clean[tid]))
    defense = [
        schemas.DefenseRow(
            rank=r, team_id=tid, team_name=teams[tid], played=played[tid], goals_against=against[tid],
            average=round(avg(tid), 2), clean_sheets=clean[tid])
        for tid, r in zip(order_t, dranks)
    ]

    ty: dict[int, int] = defaultdict(int)
    tr: dict[int, int] = defaultdict(int)
    for pid in set(yellow) | set(red):
        ty[players[pid].team_id] += yellow[pid]
        tr[players[pid].team_id] += red[pid]
    fair = sorted(teams, key=lambda tid: (ty[tid] + RED_POINTS * tr[tid], tr[tid], teams[tid]))
    fair_play = [
        schemas.FairPlayRow(team_id=tid, team_name=teams[tid], yellow=ty[tid], red=tr[tid], points=ty[tid] + RED_POINTS * tr[tid])
        for tid in fair
    ]

    return schemas.StatsOut(
        matches_played=len(finished), total_goals=total_goals,
        goals_per_match=round(total_goals / len(finished), 2) if finished else 0.0,
        scorers=scorers, cards=cards, defense=defense, fair_play=fair_play,
        suspensions=tournament_suspensions(db, t),
    )
