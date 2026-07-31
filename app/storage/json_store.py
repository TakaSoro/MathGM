from __future__ import annotations

import json
import math
from pathlib import Path

from app.models.schemas import *

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp.replace(path)


class JsonStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR

    def _path(self, name: str) -> Path:
        return self.data_dir / name

    def load_config(self) -> Config:
        data = _read_json(self._path("config.json"), {})
        return Config.model_validate(data)

    def load_player(self) -> Player:
        data = _read_json(self._path("player.json"), {})
        return Player.model_validate(data)

    def load_season(self) -> Season:
        data = _read_json(self._path("season.json"), {})
        return Season.model_validate(data)

    def load_season_history(self) -> list[SeasonHistory]:
        data = _read_json(self._path("season_history.json"), [])
        return [SeasonHistory.model_validate(item) for item in data]

    def load_games(self) -> list[dict]:
        return _read_json(self._path("games.json"), [])

    def load_league_players(self) -> list[AIPlayer]:
        data = _read_json(self._path("league_players.json"), [])
        return [AIPlayer.model_validate(item) for item in data]

    def load_team_rosters(self) -> list[TeamRoster]:
        data = _read_json(self._path("team_rosters.json"), [])
        return [TeamRoster.model_validate(item) for item in data]

    def save_team_rosters(self, rosters: list[TeamRoster]) -> None:
        _write_json(self._path("team_rosters.json"), [r.model_dump() for r in rosters])

    def load_game_matchups(self) -> list[dict]:
        return _read_json(self._path("game_matchups.json"), [])

    def save_game_matchups(self, matchups: list[dict]) -> None:
        _write_json(self._path("game_matchups.json"), matchups)

    def save_player(self, player: Player) -> None:
        _write_json(self._path("player.json"), player.model_dump())

    def save_season(self, season: Season) -> None:
        _write_json(self._path("season.json"), season.model_dump())

    def save_season_history(self, history: list[SeasonHistory]) -> None:
        _write_json(
            self._path("season_history.json"), [h.model_dump() for h in history]
        )

    def save_games(self, games: list[dict]) -> None:
        _write_json(self._path("games.json"), games)

    def save_league_players(self, players: list[AIPlayer]) -> None:
        _write_json(
            self._path("league_players.json"), [p.model_dump() for p in players]
        )

    def save_all(
        self,
        player: Player,
        season: Season,
        games: list[dict],
        league_players: list[AIPlayer] | None = None,
    ) -> None:
        self.save_player(player)
        self.save_season(season)
        self.save_games(games)
        if league_players is not None:
            self.save_league_players(league_players)

    def reset_season(self) -> None:
        myplayer = self.load_player()
        myplayer.stats = PlayerStats()
        myplayer.streak = StreakData()
        myplayer.totals = PlayerTotals()
        seed_season = Season()
        self.save_player(myplayer)
        self.save_season(seed_season)
        self.save_games([])
        league_players = self.load_league_players()
        for player in league_players:
            player.last_game = None
            player.last_game_mvp = 0.0
            player.wins = 0
            player.losses = 0
            player.streak = 0
            player.games_played = 0
            player.total_pts = 0
            player.total_ast = 0
            player.total_reb = 0
            player.total_stl = 0
            player.total_blk = 0
            player.total_to = 0
            player.total_mvp = 0

        self.save_league_players(league_players)
        self.save_game_matchups([])
        self.save_team_rosters([])

    def reset_career(self) -> None:
        self.reset_season()
        league_players = self.load_league_players()

        for player in league_players:
            player.career_totals = CareerTotals()

        self.save_league_players(league_players)
        self.save_season_history([])

        myplayer = self.load_player()
        myplayer.career_totals = CareerTotals()
        self.save_player(myplayer)


    def archive_completed_season(
        self, season: Season, games: list[dict], final_rank: int | None = None
    ) -> None:
        history = self.load_season_history()
        history.append(
            SeasonHistory(
                year=season.year,
                label=season.label,
                final_record=f"{season.player_record.wins}-{season.player_record.losses}",
                final_rank=final_rank,
            )
        )
        self.save_season_history(history)

    def start_new_season(self, player: Player) -> Season:
        config = self.load_config()
        history = self.load_season_history()
        season_num = len(history)
        new_year = config.season_year + season_num

        from app.models.schemas import SEASON_LABELS

        label_idx = min(season_num, len(SEASON_LABELS) - 1)
        new_label = (
            SEASON_LABELS[label_idx]
            if season_num < len(SEASON_LABELS)
            else f"Season {season_num + 1}"
        )

        new_season = Season(year=new_year, label=new_label)
        self.save_season(new_season)

        player.totals = PlayerTotals()
        player.streak = StreakData()
        for stat in player.stats.model_dump():
            setattr(player.stats, stat, 50)
        player.career_totals.seasons_played += 1
        self.save_player(player)

        league_players = self.load_league_players()
        for player in league_players:
            player.last_game = None
            player.last_game_mvp = 0.0
            player.wins = 0
            player.losses = 0
            player.streak = 0
            player.games_played = 0
            player.total_pts = 0
            player.total_ast = 0
            player.total_reb = 0
            player.total_stl = 0
            player.total_blk = 0
            player.total_to = 0
            player.total_mvp = 0
            player.is_rookie = False
        self.save_league_players(league_players)

        return new_season


store = JsonStore()
