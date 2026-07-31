import random
import math
import numpy as np
from scipy.stats import truncnorm
from app.models.schemas import AIPlayer, BoxScore, Config, GameInput, GameMatchup, TeamRoster
from app.engine.game_engine import (
    compute_box_score,
    compute_bonuses,
    compute_mvp_score,
    get_streak_multiplier,
    simulate_box_score_from_ovr,
)

def simulate_ai_player_day(
    ai_player: AIPlayer,
    player_ovr: int,
    player_last_mvp: float,
    config: Config,
) -> dict:
    # 1. Rubberband the Rival AI's OVR based on player OVR
    if ai_player.is_rival:
        # Keep Hypatia's OVR dynamically tied to player's OVR, but with a minimum of 78
        target_ovr = max(75, player_ovr + random.choice([-1, 0, 1, 2]))
        # Smoothly transition her OVR towards target
        if ai_player.ovr < target_ovr:
            ai_player.ovr += 1
        elif ai_player.ovr > target_ovr:
            ai_player.ovr -= 1
        # Rival motivation boost flag
        has_rival_boost = player_last_mvp >= 40.0
    else:
        has_rival_boost = False

    # 2. Determine if AI studies today
    active_prob = 0.70 + (ai_player.ovr / 400.0)  # e.g., 90 OVR has 92.5% chance
    is_active = random.random() < active_prob

    if is_active:
        # Scale inputs using OVR
        ovr_factor = ai_player.ovr ** 2 / 4900
        
        # Base hours
        math_hours = max(0.0, random.normalvariate(ovr_factor * 2, 1.0))
        physics_hours = max(0.0, random.normalvariate(ovr_factor * 2, 1.0))
        cs_hours = max(0.0, random.normalvariate(ovr_factor * 2, 1.0))
        
        # Clamps
        math_hours = min(16.0, math_hours)
        physics_hours = min(8.0, physics_hours)
        cs_hours = min(8.0, cs_hours)
        
        # Rival motivation boost adds stats
        if has_rival_boost:
            math_hours += random.uniform(0.5, 1.5)
            physics_hours += random.uniform(0.5, 1.5)
            cs_hours += random.uniform(0.5, 1.5)
            
        reading_minutes = max(0, int(random.normalvariate(ovr_factor * 45, 30)))
        homeworks_done = max(0, int(random.normalvariate(ovr_factor * 0.8, 0.5)))
        misconceptions_fixed = max(0, int(random.normalvariate(ovr_factor * 0.8, 0.5)))
        new_things_learned = max(0, int(random.normalvariate(ovr_factor * 1.2, 0.5)))
        
        game_input = GameInput(
            math_hours=round(math_hours, 1),
            physics_hours=round(physics_hours, 1),
            cs_hours=round(cs_hours, 1),
            homeworks_done=homeworks_done,
            misconceptions_fixed=misconceptions_fixed,
            new_things_learned=new_things_learned,
            reading_minutes=reading_minutes,
        )
    else:
        game_input = GameInput(
            math_hours=0.0,
            physics_hours=0.0,
            cs_hours=0.0,
            homeworks_done=0,
            misconceptions_fixed=0,
            new_things_learned=0,
            reading_minutes=0,
        )

    # 3. Calculate streak and box score
    studied = (game_input.math_hours + game_input.physics_hours + game_input.cs_hours) > 0
    if studied:
        ai_player.streak += 1
    else:
        ai_player.streak = 0

    streak_mult = get_streak_multiplier(ai_player.streak, config)
    box_score = simulate_box_score_from_ovr(
        ai_player.ovr,
        is_rookie=ai_player.is_rookie,
        is_active=studied,
    )
    bonuses = compute_bonuses(game_input, box_score, config) if studied else []
    mvp_score = compute_mvp_score(box_score, bonuses, config)
    
    # Update AI Player totals
    ai_player.games_played += 1
    ai_player.total_pts += box_score.PTS
    ai_player.total_ast += box_score.AST
    ai_player.total_reb += box_score.REB
    ai_player.total_stl += box_score.STL
    ai_player.total_blk += box_score.BLK
    ai_player.total_to += box_score.TO
    ai_player.total_mvp += mvp_score
    ai_player.career_totals.games_played += 1
    ai_player.career_totals.total_pts += box_score.PTS
    ai_player.career_totals.total_ast += box_score.AST
    ai_player.career_totals.total_reb += box_score.REB
    ai_player.career_totals.total_stl += box_score.STL
    ai_player.career_totals.total_blk += box_score.BLK
    ai_player.career_totals.total_to += box_score.TO
    ai_player.career_totals.total_mvp += mvp_score
    
    # Store last game
    ai_player.last_game = box_score
    ai_player.last_game_mvp = mvp_score
    
    # Return player stats for this game
    return {
        "name": ai_player.name,
        "team": ai_player.team,
        "ovr": ai_player.ovr,
        "box_score": box_score.model_dump(),
        "mvp_score": mvp_score,
        "bonuses": bonuses
    }

def get_truncated_normal(mean=0, sd=1, low=0, upp=10):
    # Standardize the boundaries for the truncnorm function
    a_param = (low - mean) / sd
    b_param = (upp - mean) / sd
    
    # Generate the samples
    return truncnorm.rvs(a_param, b_param, loc=mean, scale=sd)

def generate_team_roster(team_name: str, num_players: int = 5) -> TeamRoster:
    """Generate a random team roster with specified number of players."""
    first_names = ["James", "Michael", "David", "Chris", "Daniel", "Matthew", "Andrew", "Joshua", "Ryan", "Brandon",
                   "Emma", "Olivia", "Ava", "Sophia", "Isabella", "Mia", "Charlotte", "Amelia", "Harper", "Evelyn"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Anderson", "Taylor", "Thomas", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris"]
    
    positions = ["Point Geometer", "Shooting Analyst", "Power Algebraist", "Center Relativist", "Fluxion Forward"]
    
    players = []
    for i in range(num_players):
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"
        
        # Random OVR between 30-69
        ovr = int(get_truncated_normal(mean=44.5, sd=30, low=20, upp=69).round())
        
        # Random position
        position = positions[i % len(positions)]
        
        player = AIPlayer(
            name=name,
            team=team_name,
            position=position,
            ovr=ovr,
            is_rookie=random.choice([True, False]),
            is_rival=False
        )
        players.append(player)
    
    return TeamRoster(team_name=team_name, players=players)


def generate_full_league_rosters(team_names: list[str]) -> list[TeamRoster]:
    """Generate rosters for all teams in the league."""
    return [generate_team_roster(team) for team in team_names]


def simulate_league_day(
    ai_players: list[AIPlayer],
    player_overall_rating: int,
    player_last_game_mvp: float,
    player_team_name: str,
    player_win: bool,
    config: Config,
    player_box_score: BoxScore,
    team_rosters_by_name: dict[str, list[AIPlayer]] | None = None,
) -> list[GameMatchup]:
    # 1. Simulate game for each AI player
    for ai in ai_players:
        simulate_ai_player_day(ai, player_overall_rating, player_last_game_mvp, config)

    # 2. Build full team entries from rosters
    from collections import defaultdict

    rosters = team_rosters_by_name or {}

    # User team: Melphin + every player on his roster
    user_roster = rosters.get(player_team_name, [])
    user_players = [
        {
            "name": rp.name,
            "team": rp.team,
            "ovr": rp.ovr,
            "box_score": rp.last_game.model_dump() if rp.last_game else None,
            "mvp_score": rp.last_game_mvp,
        }
        for rp in user_roster
    ]
    user_players.insert(
        0,
        {
            "name": "Melphin",
            "team": player_team_name,
            "ovr": player_overall_rating,
            "box_score": player_box_score.model_dump(),
            "mvp_score": player_last_game_mvp,
        },
    )

    all_teams: list[dict] = [
        {
            "name": player_team_name,
            "is_user": True,
            "mvp_score": player_last_game_mvp,
            "win": player_win,
            "obj": None,
            "players": user_players,
        }
    ]

    # AI teams: group simulated players by team name
    ai_team_map: dict[str, list[AIPlayer]] = defaultdict(list)
    for ai in ai_players:
        ai_team_map[ai.team].append(ai)

    for team_name, players in ai_team_map.items():
        if team_name == all_teams[0]["name"]:
            continue
        all_teams.append(
            {
                "name": team_name,
                "is_user": False,
                "mvp_score": max(p.last_game_mvp for p in players),
                "win": False,
                "obj": players,
                "players": [
                    {
                        "name": p.name,
                        "team": p.team,
                        "ovr": p.ovr,
                        "box_score": p.last_game.model_dump() if p.last_game else None,
                        "mvp_score": p.last_game_mvp,
                    }
                    for p in players
                ],
            }
        )

    # 3. Pair them 2-by-2 and track matchups
    random.shuffle(all_teams)

    matchups = []
    paired = set()
    for i in range(len(all_teams)):
        if i in paired:
            continue
        for j in range(i + 1, len(all_teams)):
            if j not in paired:
                t1 = all_teams[i]
                t2 = all_teams[j]
                paired.add(i)
                paired.add(j)

                team_score1 = sum((p.get("box_score") or {}).get("PTS", 0) for p in t1.get("players", []))
                team_score2 = sum((p.get("box_score") or {}).get("PTS", 0) for p in t2.get("players", []))

                if team_score1 > team_score2:
                    t1_win = True
                    t2_win = False
                elif team_score2 > team_score1:
                    t1_win = False
                    t2_win = True
                else:
                    team1_ovr_avg = sum(p.get("ovr", 0) for p in t1.get("players", [])) / max(1, len(t1.get("players", [])))
                    team2_ovr_avg = sum(p.get("ovr", 0) for p in t2.get("players", [])) / max(1, len(t2.get("players", [])))
                    if team1_ovr_avg > team2_ovr_avg:
                        t1_win = True
                        t2_win = False
                    elif team2_ovr_avg > team1_ovr_avg:
                        t1_win = False
                        t2_win = True
                    else:
                        t1_win = random.choice([True, False])
                        t2_win = not t1_win

                matchup = GameMatchup(
                    day=0,
                    team1_name=t1["name"],
                    team2_name=t2["name"],
                    team1_score=team_score1,
                    team2_score=team_score2,
                    winner=t1["name"] if t1_win else t2["name"],
                    team1_players=t1.get("players", []),
                    team2_players=t2.get("players", []),
                )
                matchups.append(matchup)

                if not t1["is_user"]:
                    for ai in t1.get("obj", []):
                        if t1_win:
                            ai.wins += 1
                        else:
                            ai.losses += 1
                if not t2["is_user"]:
                    for ai in t2.get("obj", []):
                        if t2_win:
                            ai.wins += 1
                        else:
                            ai.losses += 1
                break

    return matchups
