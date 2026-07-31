from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.engine.game_engine import (
    get_streak_tier_name,
    player_overall,
    process_submit_day,
)
from app.models.schemas import AIPlayer, CareerTotals, GameInput, Player, ProjectStatus, SeasonHistory, STAT_LABELS
from app.storage.json_store import store
from app.engine.league_engine import simulate_league_day, generate_full_league_rosters

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

BONUS_LABELS = {
    "triple_double": "Triple Double",
    "clutch": "Clutch Study (8+ hrs)",
    "homework_marathon": "Homework Marathon",
    "all_rounder": "All-Rounder",
}


def make_player_summary(name, team, is_rookie, is_rival, ovr, gp, pts, ast, reb, stl, blk, to, mvp_score, wins, losses, is_user=False):
    avg_pts = round(pts / gp, 1) if gp > 0 else 0.0
    avg_ast = round(ast / gp, 1) if gp > 0 else 0.0
    avg_reb = round(reb / gp, 1) if gp > 0 else 0.0
    avg_stl = round(stl / gp, 1) if gp > 0 else 0.0
    avg_blk = round(blk / gp, 1) if gp > 0 else 0.0
    avg_to = round(to / gp, 1) if gp > 0 else 0.0
    avg_mvp = round(mvp_score / gp, 1) if gp > 0 else 0.0
    
    return {
        "name": name,
        "team": team,
        "is_rookie": is_rookie,
        "is_rival": is_rival,
        "ovr": ovr,
        "games_played": gp,
        "avg_pts": avg_pts,
        "avg_ast": avg_ast,
        "avg_reb": avg_reb,
        "avg_stl": avg_stl,
        "avg_blk": avg_blk,
        "avg_to": avg_to,
        "avg_mvp": avg_mvp,
        "wins": wins,
        "losses": losses,
        "is_user": is_user,
    }


def generate_news(games, player, season, league_players) -> list[str]:
    if not games:
        return [
            "Mathematical Basketball Association (MBA) 2026 Season tips off today!",
            "Rookie Melphin looks to make a statement with the Seoul Science Dragons.",
            "Rival rookie Hypatia 'Hyperbola' H. is reported to be in top academic shape."
        ]
    
    last_game = games[-1]
    day = last_game["day"]
    user_mvp = last_game["mvp_score"]
    user_result = last_game["result"]
    
    news = []
    
    if user_result == "W":
        news.append(f"Day {day}: Seoul Science Dragons secure a crucial victory behind Melphin's {user_mvp} MVP effort!")
    else:
        news.append(f"Day {day}: Dragons fall short as Melphin struggles to find consistency. Daily benchmark missed.")
        
    rival = next((p for p in league_players if p.is_rival), None)
    if rival and rival.last_game:
        rival_mvp = rival.last_game_mvp
        if user_mvp > rival_mvp:
            if user_mvp > 0:
                news.append(f"Rivalry: Melphin outscores Hypatia ({user_mvp} vs {rival_mvp} MVP) on Day {day}. Advantage, Melphin!")
            else:
                news.append(f"Rivalry: Melphin sits out (DNP). Hypatia capitalized with a {rival_mvp} MVP score and posts: 'Consistency is everything.'")
        elif rival_mvp > user_mvp:
            news.append(f"Rivalry: Hypatia outshines Melphin with a stellar {rival_mvp} MVP performance. 'Just getting started,' she tweets.")
        else:
            news.append(f"Rivalry: Melphin and Hypatia finish Day {day} in a dead heat with identical {user_mvp} MVP scores!")
            
    top_performer = None
    top_score = user_mvp
    top_name = player.name
    top_stat_line = f"{last_game['box_score']['PTS']} PTS, {last_game['box_score']['AST']} AST"
    
    for ai in league_players:
        if ai.last_game and ai.last_game_mvp > top_score:
            top_score = ai.last_game_mvp
            top_name = ai.name
            top_stat_line = f"{ai.last_game.PTS} PTS, {ai.last_game.AST} AST, {ai.last_game.REB} REB"
            top_performer = ai
            
    if top_name == player.name:
        if user_mvp >= 40:
            news.append(f"Highlight: Melphin dominates the league today with a massive {user_mvp} MVP performance!")
    else:
        news.append(f"Highlight: {top_name} leads the league on Day {day} with a dominant {top_score} MVP game ({top_stat_line})!")
        
    if player.streak.current >= 7:
        news.append(f"Streak Alert: Melphin is on a {player.streak.current}-day study streak! Can anyone stop them?")
    elif rival and rival.streak >= 7:
        news.append(f"Streak Alert: Rival Hypatia is heating up with a {rival.streak}-day streak!")
        
    return news


def build_context() -> dict:
    player = store.load_player()
    season = store.load_season()
    config = store.load_config()
    games = store.load_games()
    last_game = games[-1] if games else None
    season_history = store.load_season_history()

    # Load league players (initialize if empty)
    league_players = store.load_league_players()

    # Compute summaries
    user_gp = player.totals.games_played
    user_pts = sum(g['box_score']['PTS'] for g in games)
    user_ast = sum(g['box_score']['AST'] for g in games)
    user_reb = sum(g['box_score']['REB'] for g in games)
    user_stl = sum(g['box_score']['STL'] for g in games)
    user_blk = sum(g['box_score']['BLK'] for g in games)
    user_to = sum(g['box_score']['TO'] for g in games)
    user_mvp = sum(g['mvp_score'] for g in games)

    user_summary = make_player_summary(
        name=player.name,
        team=player.team,
        is_rookie=True,
        is_rival=False,
        ovr=player_overall(player),
        gp=user_gp,
        pts=user_pts,
        ast=user_ast,
        reb=user_reb,
        stl=user_stl,
        blk=user_blk,
        to=user_to,
        mvp_score=user_mvp,
        wins=season.player_record.wins,
        losses=season.player_record.losses,
        is_user=True
    )

    all_summaries = [user_summary]
    for ai in league_players:
        all_summaries.append(make_player_summary(
            name=ai.name,
            team=ai.team,
            is_rookie=ai.is_rookie,
            is_rival=ai.is_rival,
            ovr=ai.ovr,
            gp=ai.games_played,
            pts=ai.total_pts,
            ast=ai.total_ast,
            reb=ai.total_reb,
            stl=ai.total_stl,
            blk=ai.total_blk,
            to=ai.total_to,
            mvp_score=ai.total_mvp,
            wins=ai.wins,
            losses=ai.losses,
            is_user=False
        ))

    season_pts_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_pts": player.totals.total_pts, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_pts_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_pts": ai.total_pts,
            "season_gp": ai.games_played,
        })
    season_rankings_pts = sorted(season_pts_list, key=lambda x: x["season_pts"]/(x["season_gp"] or 1), reverse=True)

    season_ast_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_ast": player.totals.total_ast, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_ast_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_ast": ai.total_ast,
            "season_gp": ai.games_played,
        })
    season_rankings_ast = sorted(season_ast_list, key=lambda x: x["season_ast"]/(x["season_gp"] or 1), reverse=True)

    season_reb_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_reb": player.totals.total_reb, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_reb_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_reb": ai.total_reb,
            "season_gp": ai.games_played,
        })
    season_rankings_reb = sorted(season_reb_list, key=lambda x: x["season_reb"]/(x["season_gp"] or 1), reverse=True)

    season_stl_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_stl": player.totals.total_stl, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_stl_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_stl": ai.total_stl,
            "season_gp": ai.games_played,
        })
    season_rankings_stl = sorted(season_stl_list, key=lambda x: x["season_stl"]/(x["season_gp"] or 1), reverse=True)

    season_blk_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_blk": player.totals.total_blk, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_blk_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_blk": ai.total_blk,
            "season_gp": ai.games_played,
        })
    season_rankings_blk = sorted(season_blk_list, key=lambda x: x["season_blk"]/(x["season_gp"] or 1), reverse=True)

    season_to_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_to": player.totals.total_to, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_to_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_to": ai.total_to,
            "season_gp": ai.games_played,
        })
    season_rankings_to = sorted(season_to_list, key=lambda x: x["season_to"]/(x["season_gp"] or 1), reverse=True)

    season_mvp_list = [
        {"name": player.name, "team": player.team, "is_rookie": player.career_totals.seasons_played == 0, "is_user": True, "season_mvp": player.totals.total_mvp, "season_gp": player.totals.games_played}
    ]
    for ai in league_players:
        season_mvp_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "season_mvp": ai.total_mvp,
            "season_gp": ai.games_played,
        })
    season_rankings_mvp = sorted(season_mvp_list, key=lambda x: x["season_mvp"]/(x["season_gp"] or 1), reverse=True)

    season_rookie_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "season_mvp": player.totals.total_mvp, "season_gp": player.totals.games_played}
    ] if player.career_totals.seasons_played == 0 else []
    for ai in league_players:
        if ai.is_rookie:
            season_rookie_list.append({
                "name": ai.name,
                "team": ai.team,
                "is_rookie": ai.is_rookie,
                "is_user": False,
                "season_mvp": ai.total_mvp,
                "season_gp": ai.games_played,
            })
    season_rankings_rookie = sorted(season_rookie_list, key=lambda x: x["season_mvp"]/(x["season_gp"] or 1), reverse=True)

    # Career Rankings (based on total stats, which represent career for AI players)
    career_pts_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_pts": player.career_totals.total_pts, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_pts_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_pts": ai.career_totals.total_pts,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_pts = sorted(career_pts_list, key=lambda x: x["career_pts"], reverse=True)

    # Career AST Rankings
    career_ast_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_ast": player.career_totals.total_ast, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_ast_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_ast": ai.career_totals.total_ast,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_ast = sorted(career_ast_list, key=lambda x: x["career_ast"], reverse=True)

    # Career REB Rankings
    career_reb_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_reb": player.career_totals.total_reb, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_reb_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_reb": ai.career_totals.total_reb,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_reb = sorted(career_reb_list, key=lambda x: x["career_reb"], reverse=True)

    career_stl_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_stl": player.career_totals.total_stl, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_reb_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_stl": ai.career_totals.total_stl,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_stl = sorted(career_stl_list, key=lambda x: x["career_stl"], reverse=True)

    career_blk_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_blk": player.career_totals.total_blk, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_blk_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_blk": ai.career_totals.total_blk,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_blk = sorted(career_blk_list, key=lambda x: x["career_blk"], reverse=True)

    career_to_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_to": player.career_totals.total_to, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_reb_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_to": ai.career_totals.total_to,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_to = sorted(career_to_list, key=lambda x: x["career_to"], reverse=True)

    career_mvp_list = [
        {"name": player.name, "team": player.team, "is_rookie": True, "is_user": True, "career_mvp": player.career_totals.total_mvp, "career_gp": player.career_totals.games_played}
    ]
    for ai in league_players:
        career_reb_list.append({
            "name": ai.name,
            "team": ai.team,
            "is_rookie": ai.is_rookie,
            "is_user": False,
            "career_mvp": ai.career_totals.total_mvp,
            "career_gp": ai.career_totals.games_played,
        })
    career_rankings_mvp = sorted(career_mvp_list, key=lambda x: x["career_mvp"], reverse=True)

    # Rival Head-to-Head
    rival_player = next((p for p in league_players if p.is_rival), None)
    rival_summary = next((p for p in all_summaries if p["is_rival"]), None)

    # Standings (Eastern and Western Conferences)
    eastern_standings = sorted(
        [p for p in all_summaries if p["team"] in [
            "Seoul Science Dragons", "Alexandria Alphas", "Princeton Relativists",
            "Cambridge Calculators", "London Analytical", "Bletchley Decoders"
        ]],
        key=lambda x: (x["wins"], x["ovr"]),
        reverse=True
    )
    
    western_standings = sorted(
        [p for p in all_summaries if p["team"] in [
            "Göttingen Geometers", "NASA Orbiters", "Paris Theory",
            "Erlangen Algebra", "Basel Analysis", "Madras Mock Theta"
        ]],
        key=lambda x: (x["wins"], x["ovr"]),
        reverse=True
    )

    # Generate News
    news = generate_news(games, player, season, league_players)

    return {
        "player": player,
        "player_stats": player.stats.model_dump(),
        "season": season,
        "season_history": [h.model_dump() for h in season_history],
        "config": config,
        "games": games,
        "last_game": last_game,
        "overall": player_overall(player),
        "stat_labels": STAT_LABELS,
        "streak_tier": get_streak_tier_name(player.streak.current),
        "bonus_labels": BONUS_LABELS,
        "season_complete": season.is_complete,
        "career_rankings_pts": career_rankings_pts,
        "career_rankings_ast": career_rankings_ast,
        "career_rankings_reb": career_rankings_reb,
        "career_rankings_stl": career_rankings_stl,
        "career_rankings_blk": career_rankings_blk,
        "career_rankings_to": career_rankings_to,
        "career_rankings_mvp": career_rankings_mvp,
        "season_rankings_pts": season_rankings_pts,
        "season_rankings_ast": season_rankings_ast,
        "season_rankings_reb": season_rankings_reb,
        "season_rankings_stl": season_rankings_stl,
        "season_rankings_blk": season_rankings_blk,
        "season_rankings_to": season_rankings_to,
        "season_rankings_mvp": season_rankings_mvp,
        "season_rankings_rookie": season_rankings_rookie,
        "rival_player": rival_player,
        "rival_summary": rival_summary,
        "eastern_standings": eastern_standings,
        "western_standings": western_standings,
        "news": news,
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        build_context(),
    )


@router.get("/partials/dashboard-main", response_class=HTMLResponse)
async def dashboard_main(request: Request):
    ctx = build_context()
    ctx["toast"] = request.query_params.get("toast")
    ctx["toast_type"] = request.query_params.get("toast_type", "win")
    return templates.TemplateResponse(
        request,
        "partials/dashboard_main.html",
        ctx,
    )


@router.get("/api/state")
async def api_state():
    ctx = build_context()
    return JSONResponse(
        {
            "player": ctx["player"].model_dump(),
            "season": ctx["season"].model_dump(),
            "games": ctx["games"],
            "overall": ctx["overall"],
        }
    )


@router.get("/api/games")
async def api_games():
    return JSONResponse(store.load_games())


@router.get("/api/game/{game_day}")
async def api_game_detail(game_day: int):
    """Get detailed stats for a specific game day."""
    games = store.load_games()
    game = next((g for g in games if g["day"] == game_day), None)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    matchups = store.load_game_matchups()
    day_matchups = [m for m in matchups if m["day"] == game_day]
    
    return JSONResponse({
        "game": game,
        "matchups": day_matchups
    })


@router.get("/api/rosters")
async def api_rosters():
    """Get all team rosters."""
    rosters = store.load_team_rosters()
    return JSONResponse([r.model_dump() for r in rosters])


@router.post("/api/initialize-rosters")
async def initialize_rosters():
    """Generate and save team rosters for all teams."""
    team_names = [
        "Seoul Science Dragons", "Alexandria Alphas", "Princeton Relativists",
        "Cambridge Calculators", "London Analytical", "Bletchley Decoders",
        "Göttingen Geometers", "NASA Orbiters", "Paris Theory",
        "Erlangen Algebra", "Basel Analysis", "Madras Mock Theta"
    ]
    
    rosters = generate_full_league_rosters(team_names)
    store.save_team_rosters(rosters)
    
    return JSONResponse({"status": "success", "teams": len(rosters)})


@router.post("/api/submit-day", response_class=HTMLResponse)
async def submit_day(
    request: Request,
    math_hours: float = Form(0),
    physics_hours: float = Form(0),
    cs_hours: float = Form(0),
    homeworks_done: int = Form(0),
    misconceptions_fixed: int = Form(0),
    new_things_learned: int = Form(0),
    reading_minutes: int = Form(0),
):
    player = store.load_player()
    season = store.load_season()
    config = store.load_config()
    games = store.load_games()

    if season.is_complete:
        raise HTTPException(status_code=400, detail="Season is complete.")

    game_input = GameInput(
        math_hours=math_hours,
        physics_hours=physics_hours,
        cs_hours=cs_hours,
        homeworks_done=homeworks_done,
        misconceptions_fixed=misconceptions_fixed,
        new_things_learned=new_things_learned,
        reading_minutes=reading_minutes,
    )

    try:
        league_players = store.load_league_players()

        record = process_submit_day(game_input, player, season, config)

        player_won = record.result == "W"
        player_last_mvp = record.mvp_score
        player_ovr = player_overall(player)

        team_rosters = store.load_team_rosters()
        if not team_rosters:
            from app.engine.league_engine import generate_full_league_rosters
            team_names = list({p.team for p in league_players} | {player.team})
            team_rosters = generate_full_league_rosters(team_names)

        roster_map = {r.team_name: r.players for r in team_rosters}
        all_roster_players = []
        for r in team_rosters:
            all_roster_players.extend(r.players)

        matchups = simulate_league_day(
            ai_players=list(league_players) + all_roster_players,
            player_overall_rating=player_ovr,
            player_last_game_mvp=player_last_mvp,
            player_team_name=player.team,
            player_win=player_won,
            config=config,
            player_box_score=record.box_score,
            team_rosters_by_name=roster_map,
        )

        store.save_team_rosters(team_rosters)
        
        # Set day number for matchups
        for matchup in matchups:
            matchup.day = record.day
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    games.append(record.model_dump())
    
    # Save matchups
    existing_matchups = store.load_game_matchups()
    existing_matchups.extend([m.model_dump() for m in matchups])
    store.save_game_matchups(existing_matchups)
    
    new_season_started = False
    if season.is_complete:
        user_gp = player.totals.games_played
        user_pts = sum(g['box_score']['PTS'] for g in games)
        user_ast = sum(g['box_score']['AST'] for g in games)
        user_reb = sum(g['box_score']['REB'] for g in games)
        user_stl = sum(g['box_score']['STL'] for g in games)
        user_blk = sum(g['box_score']['BLK'] for g in games)
        user_to = sum(g['box_score']['TO'] for g in games)
        user_mvp = sum(g['mvp_score'] for g in games)

        user_summary_rank = make_player_summary(
            name=player.name,
            team=player.team,
            is_rookie=True,
            is_rival=False,
            ovr=player_overall(player),
            gp=user_gp,
            pts=user_pts,
            ast=user_ast,
            reb=user_reb,
            stl=user_stl,
            blk=user_blk,
            to=user_to,
            mvp_score=user_mvp,
            wins=season.player_record.wins,
            losses=season.player_record.losses,
            is_user=True
        )
        all_rank_summaries = [user_summary_rank]
        for ai in league_players:
            all_rank_summaries.append(make_player_summary(
                name=ai.name,
                team=ai.team,
                is_rookie=ai.is_rookie,
                is_rival=ai.is_rival,
                ovr=ai.ovr,
                gp=ai.games_played,
                pts=ai.total_pts,
                ast=ai.total_ast,
                reb=ai.total_reb,
                stl=ai.total_stl,
                blk=ai.total_blk,
                to=ai.total_to,
                mvp_score=ai.total_mvp,
                wins=ai.wins,
                losses=ai.losses,
                is_user=False
            ))

        sorted_by_mvp = sorted(all_rank_summaries, key=lambda x: (x["avg_mvp"], x["ovr"]), reverse=True)
        final_rank = next((i + 1 for i, s in enumerate(sorted_by_mvp) if s["is_user"]), 1)

        store.archive_completed_season(season, games, final_rank)
        season = store.start_new_season(player)
        games = []
        store.save_game_matchups([])
        store.save_games(games)
        new_season_started = True

    store.save_all(player, season, games, league_players)

    ctx = build_context()
    ctx["toast"] = f"Game {record.day}: {record.result} — MVP {record.mvp_score}"
    ctx["toast_type"] = "win" if record.result == "W" else "loss"
    if new_season_started:
        ctx["toast"] = f"Season Complete! Final record: {season.player_record.wins}-{season.player_record.losses}. Welcome to the {season.label}!"
        ctx["toast_type"] = "info"

    return templates.TemplateResponse(request, "dashboard.html", ctx)


@router.post("/api/reset/season")
async def reset_season(request: Request):
    store.reset_season()
    if request.headers.get("HX-Request"):
        ctx = build_context()
        ctx["toast"] = "Season reset."
        ctx["toast_type"] = "info"
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            ctx,
        )
    return JSONResponse({"status": "reset"})

@router.post("/api/reset/career")
async def reset_career(request: Request):
    store.reset_career()
    if request.headers.get("HX-Request"):
        ctx = build_context()
        ctx["toast"] = "Career reset."
        ctx["toast_type"] = "info"
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            ctx,
        )
    return JSONResponse({"status": "reset"})

@router.post("/api/regenerate")
async def regenerate_roster(request: Request):
    if request.headers.get("HX-Request"):
        team_names = [
            "Seoul Science Dragons", "Alexandria Alphas", "Princeton Relativists",
            "Cambridge Calculators", "London Analytical", "Bletchley Decoders",
            "Göttingen Geometers", "NASA Orbiters", "Paris Theory",
            "Erlangen Algebra", "Basel Analysis", "Madras Mock Theta"
        ]
        
        rosters = generate_full_league_rosters(team_names)
        store.save_team_rosters(rosters)
        ctx = build_context()
        ctx["toast"] = "Roster regeneration."
        ctx["toast_type"] = "info"
        return templates.TemplateResponse(
            request,
            "partials/dashboard_main.html",
            ctx,
        )
    return JSONResponse({"status": "regenerate"})


@router.get("/api/seasons")
async def api_seasons():
    """Get all season history."""
    history = store.load_season_history()
    season = store.load_season()
    return JSONResponse({
        "current_season": season.model_dump(),
        "history": [h.model_dump() for h in history],
    })


@router.post("/api/new-season", response_class=HTMLResponse)
async def new_season(request: Request):
    """Archive current season and start a new one."""
    player = store.load_player()
    season = store.load_season()
    config = store.load_config()
    games = store.load_games()

    if not season.is_complete:
        raise HTTPException(status_code=400, detail="Current season is not complete.")

    league_players = store.load_league_players()
    all_summaries = []

    user_gp = player.totals.games_played
    user_pts = sum(g['box_score']['PTS'] for g in games)
    user_ast = sum(g['box_score']['AST'] for g in games)
    user_reb = sum(g['box_score']['REB'] for g in games)
    user_stl = sum(g['box_score']['STL'] for g in games)
    user_blk = sum(g['box_score']['BLK'] for g in games)
    user_to = sum(g['box_score']['TO'] for g in games)
    user_mvp = sum(g['mvp_score'] for g in games)

    user_summary = make_player_summary(
        name=player.name,
        team=player.team,
        is_rookie=True,
        is_rival=False,
        ovr=player_overall(player),
        gp=user_gp,
        pts=user_pts,
        ast=user_ast,
        reb=user_reb,
        stl=user_stl,
        blk=user_blk,
        to=user_to,
        mvp_score=user_mvp,
        wins=season.player_record.wins,
        losses=season.player_record.losses,
        is_user=True
    )
    all_summaries.append(user_summary)
    for ai in league_players:
        all_summaries.append(make_player_summary(
            name=ai.name,
            team=ai.team,
            is_rookie=ai.is_rookie,
            is_rival=ai.is_rival,
            ovr=ai.ovr,
            gp=ai.games_played,
            pts=ai.total_pts,
            ast=ai.total_ast,
            reb=ai.total_reb,
            stl=ai.total_stl,
            blk=ai.total_blk,
            to=ai.total_to,
            mvp_score=ai.total_mvp,
            wins=ai.wins,
            losses=ai.losses,
            is_user=False
        ))

    sorted_by_mvp = sorted(all_summaries, key=lambda x: (x["avg_mvp"], x["ovr"]), reverse=True)
    final_rank = next((i + 1 for i, s in enumerate(sorted_by_mvp) if s["is_user"]), 1)

    store.archive_completed_season(season, games, final_rank)
    season = store.start_new_season(player)

    rosters = generate_full_league_rosters([
        "Seoul Science Dragons", "Alexandria Alphas", "Princeton Relativists",
        "Cambridge Calculators", "London Analytical", "Bletchley Decoders",
        "Göttingen Geometers", "NASA Orbiters", "Paris Theory",
        "Erlangen Algebra", "Basel Analysis", "Madras Mock Theta"
    ])
    store.save_team_rosters(rosters)
    store.save_game_matchups([])

    ctx = build_context()
    ctx["toast"] = f"Season Complete! Record: {season.player_record.wins}-{season.player_record.losses}. Welcome to the {season.label}!"
    ctx["toast_type"] = "info"
    return templates.TemplateResponse(request, "partials/dashboard_main.html", ctx)
