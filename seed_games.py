"""Seed games into the database.

Usage:
    python seed_games.py              # Seed 63 curated games
    python seed_games.py --bulk 413   # Seed N generic games (for perf testing)
"""

import random
import sys
import uuid
from datetime import datetime, timezone

from sqlmodel import select
from app.database import init_db, get_session
from app.models import Game, Platform, StorageDevice, Genre, GameGenreLink
from app.main import SEED_PLATFORMS, SEED_STORAGE

GAME_STATUSES = ["Backlog", "Jogando", "Finalizado", "Abandonado"]
COOP_PLAYERS = ["1 Jogador", "2 Jogadores", "Até 4 Jogadores", "Mais de 4 Jogadores"]
COOP_TYPES = {
    "1 Jogador": ["Um Jogador"],
    "2 Jogadores": ["Sofá"],
    "Até 4 Jogadores": ["Sofá", "Online"],
    "Mais de 4 Jogadores": ["Online", "LAN"],
}
COOP_SCREEN = ["Tela Inteira", "Tela Dividida", "Versus"]
INPUT_OPTIONS = ["Controle", "Teclado/Mouse", "Ambos"]

SCORE_OPTIONS = [None, "5/10", "6/10", "7/10", "8/10", "9/10", "10/10", "9.5"]

TITLES = [
    "Starfall Frontier",
    "Pixel Kingdom",
    "Neon Drift",
    "Crystal Caverns",
    "Iron Tide",
    "Shadow Protocol",
    "Frostbound",
    "Thunderstone Saga",
    "Void Walker",
    "Arcane Dominion",
    "Blade of Eternity",
    "Cyber Heist",
    "Duskfall",
    "Ember Wings",
    "Fractured Realms",
    "Ghost Signal",
    "Haven's Gate",
    "Infinite Descent",
    "Jade Empire Reborn",
    "Kraken's Deep",
    "Last Horizon",
    "Mirage Engine",
    "Nova Strike",
    "Obsidian Crown",
    "Phantom Fleet",
    "Quantum Drift",
    "Raven's Call",
    "Sapphire Protocol",
    "Tempest Rising",
    "Umbra Engine",
    "Vanguard Zero",
    "Wildfire Protocol",
    "Xenith Rift",
    "Zenith Border",
    "Aeon Clash",
    "Blightborne",
    "Cinder Siege",
    "Dreadnaught",
    "Echo Base",
    "Flameheart",
    "Grim Hollow",
    "Hollow Realm",
    "Iron Vanguard",
    "Jinxed",
    "Karmic Shift",
    "Lunar Break",
    "Maelstrom Rising",
    "Nightshade Protocol",
    "Overgrowth",
    "Primordial Core",
    "Rift Walker",
    "Stormbound",
    "Titanfall Legacy",
    "Underworld Protocol",
    "Vortex Gate",
    "Wild Fable",
    "Aether Drift",
    "Brass Dominion",
    "Chrono Shift",
    "Deep Six",
    "Elder Mark",
    "Fury Road",
    "Gloomhaven Digital",
]

GENRE_POOL = [
    "RPG",
    "Ação",
    "Aventura",
    "Indie",
    "Plataforma",
    "Corrida",
    "Estratégia",
    "Simulação",
    "Puzzle",
    "Rogue-like",
    "FPS",
    "Terror",
    "Mundo Aberto",
    "Família",
    "Cartas",
    "Party",
    "Dificil",
    "Cooperativo",
    "Luta",
    "Stealth",
]


def _make_game(
    session,
    title,
    platforms,
    devices,
    genres_pool,
    now,
    platform_names,
    device_names,
    genre_names,
):
    status = random.choice(GAME_STATUSES)
    coop = random.choice(COOP_PLAYERS)
    platform = platforms[random.choice(platform_names)]
    device = random.choice([None, random.choice(device_names)])

    finish_hours = None
    finish_date = None
    score = None
    replay_score = None
    if status == "Finalizado":
        finish_hours = round(random.uniform(2, 120), 1)
        finish_date = now
        score = random.choice(SCORE_OPTIONS)
        replay_score = random.randint(1, 5)

    game = Game(
        id=uuid.uuid4().hex[:12],
        title=title,
        cover_url="",
        background_url="",
        platform_id=platform.id,
        storage_device_id=devices[device].id if device else None,
        gameplay_status=status,
        interest_rating=random.randint(1, 5),
        replay_score=replay_score,
        score=score,
        must_test=random.random() < 0.15,
        finish_hours=finish_hours,
        finish_date=finish_date,
        hltb_main=random.randint(0, 80),
        hltb_main_extra=random.randint(0, 120),
        hltb_full=random.randint(0, 200),
        coop_players=coop,
        coop_type=Game.coop_type_str(COOP_TYPES.get(coop, ["Um Jogador"])),
        coop_screen_type=random.choice(COOP_SCREEN),
        input_recommendation=random.choice(INPUT_OPTIONS),
        playtime_seconds=random.randint(0, 500000),
        notes="",
        created_at=now,
        updated_at=now,
    )
    session.add(game)
    session.flush()

    num_genres = random.randint(1, 3)
    selected = random.sample(genre_names, num_genres)
    for gn in selected:
        session.add(GameGenreLink(game_id=game.id, genre_id=genres_pool[gn].id))


def seed():
    init_db()
    session = next(get_session())

    existing_platforms = session.exec(select(Platform)).all()
    platforms = {p.name: p for p in existing_platforms}

    existing_devices = session.exec(select(StorageDevice)).all()
    devices = {d.name: d for d in existing_devices}

    existing_genres = session.exec(select(Genre)).all()
    genres_pool = {g.name: g for g in existing_genres}

    for name in GENRE_POOL:
        if name not in genres_pool:
            g = Genre(name=name)
            session.add(g)
            session.flush()
            genres_pool[name] = g

    platform_names = list(platforms.keys())
    device_names = list(devices.keys())
    genre_names = list(genres_pool.keys())

    random.seed(42)

    now = datetime.now(timezone.utc).isoformat()

    for i in range(63):
        _make_game(
            session,
            TITLES[i],
            platforms,
            devices,
            genres_pool,
            now,
            platform_names,
            device_names,
            genre_names,
        )

    session.commit()
    session.close()
    print("Seeded 63 games successfully.")


def seed_bulk(count):
    init_db()
    session = next(get_session())

    existing_platforms = session.exec(select(Platform)).all()
    platforms = {p.name: p for p in existing_platforms}

    existing_devices = session.exec(select(StorageDevice)).all()
    devices = {d.name: d for d in existing_devices}

    existing_genres = session.exec(select(Genre)).all()
    genres_pool = {g.name: g for g in existing_genres}

    for name in GENRE_POOL:
        if name not in genres_pool:
            g = Genre(name=name)
            session.add(g)
            session.flush()
            genres_pool[name] = g

    platform_names = list(platforms.keys())
    device_names = list(devices.keys())
    genre_names = list(genres_pool.keys())

    now = datetime.now(timezone.utc).isoformat()

    adjectives = [
        "Magic",
        "Dark",
        "Neon",
        "Crystal",
        "Iron",
        "Shadow",
        "Frozen",
        "Thunder",
        "Void",
        "Arcane",
        "Blade",
        "Cyber",
        "Ember",
        "Fractured",
        "Ghost",
        "Infinite",
        "Jade",
        "Last",
        "Mirage",
        "Nova",
        "Obsidian",
        "Phantom",
        "Quantum",
        "Raven",
        "Sapphire",
        "Tempest",
        "Umbra",
        "Vanguard",
        "Wildfire",
        "Zenith",
        "Aeon",
        "Blight",
        "Cinder",
        "Echo",
        "Flame",
        "Grim",
        "Hollow",
        "Iron",
        "Lunar",
        "Maelstrom",
        "Nightshade",
        "Primordial",
        "Rift",
        "Storm",
        "Titan",
        "Underworld",
        "Vortex",
        "Aether",
        "Brass",
        "Chrono",
    ]

    nouns = [
        "Warrior",
        "Chronicle",
        "Rising",
        "Protocol",
        "Legacy",
        "Reckoning",
        "Descent",
        "Dominion",
        "Horizon",
        "Strike",
        "Crown",
        "Call",
        "Engine",
        "Break",
        "Shift",
        "Gate",
        "Fable",
        "Drift",
        "Siege",
        "Walker",
        "Core",
        "Haven",
        "Signal",
        "Wings",
        "Tide",
        "Kingdom",
        "Frontier",
        "Caverns",
        "Heist",
        "Realm",
        "Deep",
        "Mark",
        "Road",
        "Zero",
        "Border",
        "Clash",
        "Borne",
        "Base",
        "Heart",
        "Vanguard",
        "Protocol",
        "Rising",
        "Walker",
    ]

    for i in range(count):
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        title = f"{adj} {noun} #{i + 1:03d}"
        _make_game(
            session,
            title,
            platforms,
            devices,
            genres_pool,
            now,
            platform_names,
            device_names,
            genre_names,
        )

        if (i + 1) % 100 == 0:
            print(f"  Bulk progress: {i + 1}/{count} games...")
            session.commit()

    session.commit()
    session.close()
    print(f"Seeded {count} bulk games successfully.")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--bulk":
        count = int(sys.argv[2])
        seed_bulk(count)
    else:
        seed()
