from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from typing import List, Optional

ProjectStatus = Literal["none", "in_progress", "complete", "abandoned"]


class CareerTotals(BaseModel):
    games_played: int = 0
    projects_completed: int = 0
    projects_started: int = 0
    presentations: int = 0
    proofs_completed: int = 0
    total_pts: int = 0
    total_ast: int = 0
    total_reb: int = 0
    total_stl: int = 0
    total_blk: int = 0
    total_to: int = 0
    total_mvp: float = 0.0
    total_wins: int = 0
    total_losses: int = 0
    seasons_played: int = 0


class PlayerStats(BaseModel):
    proof: int = 50
    creativity: int = 50
    consistency: int = 50
    research_iq: int = 50
    clutch: int = 50
    communication: int = 50
    discipline: int = 50
    programming: int = 50
    physics: int = 50
    statistics: int = 50


class StreakData(BaseModel):
    current: int = 0
    longest: int = 0
    last_game_day: int | None = None


class PlayerTotals(BaseModel):
    games_played: int = 0
    projects_completed: int = 0
    projects_started: int = 0
    presentations: int = 0
    proofs_completed: int = 0
    total_pts: int = 0
    total_ast: int = 0
    total_reb: int = 0
    total_stl: int = 0
    total_blk: int = 0
    total_to: int = 0
    total_mvp: float = 0.0

class Player(BaseModel):
    id: str = "user"
    name: str = "Melphin"
    nationality: str = "KR"
    team_id: str = "Seoul Science Dragons"
    team: str = "Seoul Science Dragons"
    conference: str = "Eastern"
    division: str = "Atlantic"
    position: str = "Point Geometer"
    career_stage: str = "high_school"
    overall: float = 50
    focus: int = 50
    stamina: int = 50
    stats: PlayerStats = Field(default_factory=PlayerStats)
    streak: StreakData = Field(default_factory=StreakData)
    totals: PlayerTotals = Field(default_factory=PlayerTotals)
    career_totals: CareerTotals = Field(default_factory=CareerTotals)

class Team(BaseModel):
    id: str
    name: str
    abbreviation: str
    roster: List[Player] = []
    wins: int = 0
    losses: int = 0

class PlayerGameStats(BaseModel):
    player_id: str
    player_name: str
    pts: int
    ast: int
    reb: int
    stl: int
    blk: int
    to: int

class TeamGamePerformance(BaseModel):
    team_id: str
    team_name: str
    score: int
    player_stats: List[PlayerGameStats]

class SimulatedGame(BaseModel):
    game_id: str
    day: int
    home_team: TeamGamePerformance
    away_team: TeamGamePerformance
    is_user_game: bool = False


class SeasonHistory(BaseModel):
    year: int
    label: str
    final_record: str
    final_rank: int | None = None


class SeasonRecord(BaseModel):
    wins: int = 0
    losses: int = 0


class Season(BaseModel):
    year: int = 2026
    label: str = "Rookie Season"
    current_day: int = 1
    games_played: int = 0
    is_complete: bool = False
    player_record: SeasonRecord = Field(default_factory=SeasonRecord)


class GameInput(BaseModel):
    math_hours: float = Field(0, ge=0, le=16)
    physics_hours: float = Field(0, ge=0, le=8)
    cs_hours: float = Field(0, ge=0, le=8)
    homeworks_done: int = Field(0, ge=0, le=10)
    misconceptions_fixed: int = Field(0, ge=0, le=10)
    new_things_learned: int = Field(0, ge=0, le=10)
    reading_minutes: int = Field(0, ge=0, le=480)


class BoxScore(BaseModel):
    PTS: int = 0
    AST: int = 0
    REB: int = 0
    STL: int = 0
    BLK: int = 0
    TO: int = 0


class AIPlayer(BaseModel):
    name: str
    team: str
    conference: str = "Eastern"
    division: str = "Atlantic"
    position: str = "Point Geometer"
    is_rookie: bool = False
    is_rival: bool = False
    ovr: int
    games_played: int = 0
    total_pts: int = 0
    total_ast: int = 0
    total_reb: int = 0
    total_stl: int = 0
    total_blk: int = 0
    total_to: int = 0
    total_mvp: float = 0.0
    last_game: BoxScore | None = None
    last_game_mvp: float = 0.0
    streak: int = 0
    wins: int = 0
    losses: int = 0
    career_totals: CareerTotals = Field(default_factory=CareerTotals)


class TeamRoster(BaseModel):
    team_name: str
    players: list[AIPlayer] = Field(default_factory=list)


class GameMatchup(BaseModel):
    day: int
    team1_name: str
    team2_name: str
    team1_score: float
    team2_score: float
    winner: str
    team1_players: list[dict] = Field(default_factory=list)  # Player stats for this game
    team2_players: list[dict] = Field(default_factory=list)


class GameRecord(BaseModel):
    day: int
    date_submitted: str
    input: GameInput
    box_score: BoxScore
    mvp_score: float
    bonuses: list[str] = Field(default_factory=list)
    ability_deltas: dict[str, int] = Field(default_factory=dict)
    result: Literal["W", "L"]


class Config(BaseModel):
    season_year: int = 2026
    season_length: int = 82
    pts_per_math_hour: int = 5
    pts_per_physics_hour: int = 3
    pts_per_cs_hour: int = 4
    reb_per_reading_15min: int = 1
    ast_per_homework: int = 4
    stl_per_new_thing: int = 3
    blk_per_misconception_fixed: int = 2
    to_no_activity: int = 2
    mvp_ast_mult: float = 1.5
    mvp_reb_mult: float = 1.0
    mvp_stl_mult: float = 2.0
    mvp_blk_mult: float = 2.0
    mvp_to_penalty: float = 1.0
    triple_double_threshold: int = 10
    triple_double_bonus: int = 10
    clutch_bonus: int = 8
    homework_marathon_bonus: int = 12
    all_rounder_bonus: int = 10
    streak_milestones: list[int] = Field(default_factory=lambda: [7, 14, 30, 90])
    streak_multipliers: dict[str, float] = Field(
        default_factory=lambda: {"7": 1.05, "14": 1.08, "30": 1.12, "90": 1.20}
    )
    daily_benchmark_base: float = 35
    daily_benchmark_per_day: float = 0.2
    overall_mvp_weight: float = 0.15
    overall_growth_weight: float = 3.0


STAT_LABELS: dict[str, str] = {
    "proof": "Proof",
    "creativity": "Creativity",
    "consistency": "Consistency",
    "research_iq": "Research IQ",
    "clutch": "Clutch",
    "communication": "Communication",
    "discipline": "Discipline",
    "programming": "Programming",
    "physics": "Physics",
    "statistics": "Statistics",
}

STREAK_TIER_NAMES: dict[int, str] = {
    7: "Hot Streak",
    14: "Elite Focus",
    30: "Iron Mind",
    90: "Legendary Season",
}

SEASON_LABELS: list[str] = [
    "Rookie Season",
    "Sophomore Season"
] + ["Veteran Season"] * 100
