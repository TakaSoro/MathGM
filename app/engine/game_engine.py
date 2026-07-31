from __future__ import annotations

import math
import random
from datetime import date

from app.models.schemas import (
    STREAK_TIER_NAMES,
    BoxScore,
    Config,
    GameInput,
    GameRecord,
    Player,
    Season,
)


def get_streak_multiplier(streak: int, config: Config) -> float:
    multiplier = 1.0
    for milestone in sorted(int(k) for k in config.streak_multipliers):
        if streak >= milestone:
            multiplier = config.streak_multipliers[str(milestone)]
    return multiplier


def get_streak_tier_name(streak: int) -> str | None:
    name = None
    for milestone in sorted(STREAK_TIER_NAMES):
        if streak >= milestone:
            name = STREAK_TIER_NAMES[milestone]
    return name


def is_study_day(game_input: GameInput) -> bool:
    return game_input.math_hours + game_input.physics_hours + game_input.cs_hours > 0


def is_no_activity(game_input: GameInput) -> bool:
    return (
        game_input.math_hours
        + game_input.physics_hours
        + game_input.cs_hours
        + game_input.reading_minutes
        + game_input.homeworks_done
        + game_input.misconceptions_fixed
        + game_input.new_things_learned
        == 0
    )


def _clamp_normal_stat(value: int, lo: int, hi: int, scale: float) -> int:
    std = max(1.0, value * 0.12)
    return max(lo, min(hi, round(value * scale + random.normalvariate(0, std))))


def _clamp_stat(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def simulate_box_score_from_ovr(ovr: int, is_rookie: bool = False, is_active: bool = True) -> BoxScore:
    """Simulate a realistic game box score based on OVR."""
    base = (ovr - 50) / 10.0  # 0 at OVR 50, 5 at OVR 100

    if not is_active:
        return BoxScore(
            PTS=max(0, random.randint(0, 5)),
            AST=max(0, random.randint(0, 2)),
            REB=max(0, random.randint(0, 2)),
            STL=max(0, random.randint(0, 1)),
            BLK=0,
            TO=max(2, random.randint(1, 3)),
        )

    rookie_penalty = 0.85 if is_rookie else 1.0

    def stat(base_val: float, std: float, lo: int, hi: int) -> int:
        return max(lo, min(hi, round(random.normalvariate(base_val * rookie_penalty, std))))

    pts = stat(5 + base * 2.4, 4.0, 0, 45)
    ast = stat(1.3 + base * 0.4, 1.8, 0, 12)
    reb = stat(2.8 + base * 0.45, 2.2, 0, 14)
    stl = stat(0.6 + base * 0.2, 0.9, 0, 8)
    blk = stat(0.4 + base * 0.16, 0.7, 0, 8)
    to = max(0, min(8, round(random.normalvariate(1.8 + base * 0.08, 1.0))))

    return BoxScore(PTS=pts, AST=ast, REB=reb, STL=stl, BLK=blk, TO=to)


def compute_box_score(
    game_input: GameInput,
    config: Config,
    streak_multiplier: float,
    ovr: int = 50,
) -> BoxScore:
    raw_pts = (
        math.floor(game_input.math_hours * config.pts_per_math_hour)
        + math.floor(game_input.physics_hours * config.pts_per_physics_hour)
        + math.floor(game_input.cs_hours * config.pts_per_cs_hour)
    )
    raw_pts_scaled = math.floor(raw_pts * streak_multiplier)

    raw_ast = game_input.homeworks_done * config.ast_per_homework
    raw_reb = math.floor(game_input.reading_minutes / 15) * config.reb_per_reading_15min
    raw_stl = game_input.new_things_learned * config.stl_per_new_thing
    raw_blk = game_input.misconceptions_fixed * config.blk_per_misconception_fixed
    raw_to = config.to_no_activity if is_no_activity(game_input) else random.randint(0, 2)

    ovr_factor = max(0.45, min(1.55, (ovr - 50) / 90 + 1.0))

    pts = _clamp_normal_stat(raw_pts_scaled, 0, 45, ovr_factor)
    ast = _clamp_normal_stat(raw_ast, 0, 12, ovr_factor)
    reb = _clamp_normal_stat(raw_reb, 0, 14, ovr_factor)
    stl = _clamp_normal_stat(raw_stl, 0, 8, ovr_factor)
    blk = _clamp_normal_stat(raw_blk, 0, 8, ovr_factor)
    to = _clamp_stat(raw_to + random.randint(-1, 1), 0, 8)

    return BoxScore(PTS=pts, AST=ast, REB=reb, STL=stl, BLK=blk, TO=to)


def compute_bonuses(game_input: GameInput, box_score: BoxScore, config: Config) -> list[str]:
    bonuses: list[str] = []
    threshold = config.triple_double_threshold
    high_stats = sum(
        1
        for value in (box_score.PTS, box_score.AST, box_score.REB, box_score.STL, box_score.BLK)
        if value >= threshold
    )
    all_round_stats = all(
        value >= threshold/2
        for value in (box_score.PTS, box_score.AST, box_score.REB, box_score.STL, box_score.BLK)
    )
    if high_stats >= 3:
        bonuses.append("triple_double")
    
    # Clutch: 8+ total study hours
    total_study_hours = game_input.math_hours + game_input.physics_hours + game_input.cs_hours
    if total_study_hours >= 8.0:
        bonuses.append("clutch")
        
    # Homework Marathon: 3+ homeworks completed
    if game_input.homeworks_done >= 3:
        bonuses.append("homework_marathon")
        
    # All-Rounder
    if all_round_stats:
        bonuses.append("all_rounder")
        
    return bonuses


def bonus_points(bonuses: list[str], config: Config) -> int:
    mapping = {
        "triple_double": config.triple_double_bonus,
        "clutch": config.clutch_bonus,
        "homework_marathon": config.homework_marathon_bonus,
        "all_rounder": config.all_rounder_bonus,
    }
    return sum(mapping[b] for b in bonuses if b in mapping)


def compute_mvp_score(box_score: BoxScore, bonuses: list[str], config: Config) -> float:
    base = (
        box_score.PTS
        + box_score.AST * config.mvp_ast_mult
        + box_score.REB * config.mvp_reb_mult
        + box_score.STL * config.mvp_stl_mult
        + box_score.BLK * config.mvp_blk_mult
        - box_score.TO * config.mvp_to_penalty
    )
    return round(max(0, base + bonus_points(bonuses, config)), 1)


def daily_benchmark(day: int, config: Config) -> float:
    return config.daily_benchmark_base + day * config.daily_benchmark_per_day


def compute_result(mvp_score: float, day: int, config: Config) -> str:
    return "W" if mvp_score >= daily_benchmark(day, config) else "L"


def compute_ability_deltas(game_input: GameInput) -> dict[str, int]:
    deltas: dict[str, int] = {}

    def add(stat: str, amount: int = 1) -> None:
        deltas[stat] = deltas.get(stat, 0) + amount

    # Math hours
    if game_input.math_hours >= 2:
        add("proof")
        add("consistency")
    if game_input.math_hours >= 4:
        add("proof")

    # Physics hours
    if game_input.physics_hours >= 2:
        add("physics")
        add("consistency")
    if game_input.physics_hours >= 4:
        add("physics")

    # CS hours
    if game_input.cs_hours >= 2:
        add("programming")
        add("consistency")
    if game_input.cs_hours >= 4:
        add("programming")

    # Reading
    if game_input.reading_minutes >= 30:
        add("research_iq")
    if game_input.reading_minutes >= 60:
        add("statistics")

    # Homeworks
    if game_input.homeworks_done >= 1:
        add("discipline")
    if game_input.homeworks_done >= 2:
        add("communication")

    # Misconceptions
    if game_input.misconceptions_fixed >= 1:
        add("proof")
    if game_input.misconceptions_fixed >= 2:
        add("research_iq")

    # New things learned
    if game_input.new_things_learned >= 1:
        add("creativity")
    if game_input.new_things_learned >= 3:
        add("creativity")

    # Discipline for any active study
    if is_study_day(game_input):
        add("discipline")

    return deltas


def apply_ability_deltas(player: Player, deltas: dict[str, int]) -> None:
    stats = player.stats.model_dump()
    for stat, delta in deltas.items():
        if stat in stats:
            stats[stat] = min(99, stats[stat] + delta)
    player.stats = player.stats.model_validate(stats)


def update_streak(player: Player, season_day: int, studied: bool) -> None:
    if studied:
        if player.streak.last_game_day == season_day - 1 or player.streak.current == 0:
            player.streak.current += 1
        elif player.streak.last_game_day != season_day:
            player.streak.current = 1
        player.streak.last_game_day = season_day
        player.streak.longest = max(player.streak.longest, player.streak.current)
    else:
        player.streak.current = 0
        player.streak.last_game_day = season_day


def update_totals(player: Player, game_input: GameInput, box_score: BoxScore) -> None:
    player.totals.games_played += 1
    player.totals.projects_started += game_input.homeworks_done
    player.totals.projects_completed += game_input.homeworks_done
    player.totals.proofs_completed += game_input.misconceptions_fixed
    player.totals.total_pts += box_score.PTS
    player.totals.total_ast += box_score.AST
    player.totals.total_reb += box_score.REB
    player.totals.total_stl += box_score.STL
    player.totals.total_blk += box_score.BLK
    player.totals.total_to += box_score.TO
    player.career_totals.games_played += 1
    player.career_totals.projects_started += game_input.homeworks_done
    player.career_totals.projects_completed += game_input.homeworks_done
    player.career_totals.proofs_completed += game_input.misconceptions_fixed
    player.career_totals.total_pts += box_score.PTS
    player.career_totals.total_ast += box_score.AST
    player.career_totals.total_reb += box_score.REB
    player.career_totals.total_stl += box_score.STL
    player.career_totals.total_blk += box_score.BLK
    player.career_totals.total_to += box_score.TO


def player_overall(player: Player) -> int:
    stats = player.stats.model_dump()
    return math.floor(sum(stats.values()) / len(stats))


def process_submit_day(
    game_input: GameInput,
    player: Player,
    season: Season,
    config: Config,
) -> GameRecord:
    if season.is_complete:
        raise ValueError("Season is complete. Reset to continue.")

    day = season.current_day
    studied = is_study_day(game_input)
    streak_multiplier = get_streak_multiplier(player.streak.current + (1 if studied else 0), config)
    box_score = compute_box_score(game_input, config, streak_multiplier, ovr=player_overall(player))
    bonuses = compute_bonuses(game_input, box_score, config)
    mvp_score = compute_mvp_score(box_score, bonuses, config)
    result = compute_result(mvp_score, day, config)
    ability_deltas = compute_ability_deltas(game_input)

    apply_ability_deltas(player, ability_deltas)
    update_streak(player, day, studied)
    update_totals(player, game_input, box_score)

    if result == "W":
        season.player_record.wins += 1
    else:
        season.player_record.losses += 1
    
    player.totals.total_mvp += mvp_score
    player.career_totals.total_mvp += mvp_score

    season.games_played += 1
    season.current_day += 1
    if season.current_day > config.season_length:
        season.is_complete = True

    return GameRecord(
        day=day,
        date_submitted=date.today().isoformat(),
        input=game_input,
        box_score=box_score,
        mvp_score=mvp_score,
        bonuses=bonuses,
        ability_deltas=ability_deltas,
        result=result,
    )
