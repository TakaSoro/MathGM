# MathGM 2026

NBA 2K MyCareer-style math learning growth tracker. Local JSON storage.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000

## Phase 1 Features

- Submit Day form → box score (PTS/AST/REB/STL/BLK/TO) + MVP score
- Player ability growth, streak system, W/L record
- 82-game season tracking
- Auto-save to `data/*.json`
- 2K-style dark dashboard (mobile-first)

## Data

All game state lives in `data/`:

- `config.json` — formula constants
- `player.json` — Melphin stats & streak
- `season.json` — season progress
- `games.json` — daily game log
