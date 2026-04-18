# Import Things
import numpy as np
import pandas as pd
import streamlit as st
import base64

# Get Data
team_transition_df = pd.read_csv("team_transition_probs2026.csv")
teams_df = pd.read_csv("nhl_teams.csv")

simulation_types_dat = {"simType": ["One Game", "One Series", "1000 Games", "Entire Playoffs", "1000 Playoffs"], "nGames": [1, 7, 1000, 10, 1000]} # 10 placeholder
simulation_types_df = pd.DataFrame(simulation_types_dat)

# Get next event
def sample_next_event(current_event, team_probs):
    subset_event = team_probs[team_probs["typeDescKey"] == current_event]
    
    if len(subset_event) == 0:
        return None
    
    return np.random.choice(subset_event["next_event"], p = subset_event["prob"])

# Events where possesion switches teams
possession_switch_events = ["giveaway", "takeaway", "lost-faceoff"]

def build_transition_map(team_probs):
    transition_map = {}

    for event, group in team_probs.groupby("typeDescKey"):
        transition_map[event] = (group["next_event"].values, group["prob"].values)

    return transition_map

# Game simulation
def simulate_game(team_A_probs, team_B_probs, ta_fo_per, max_events=290):

    state = {"possession": None, "score": {"A": 0, "B": 0}, "shots": {"A": 0, "B": 0}, "shot_attempts": {"A": 0, "B": 0}, "penalties": {"A": 0, "B": 0},
             "stoppages": {"A": 0, "B": 0}, "hits": {"A": 0, "B": 0}, "blocked-shots": {"A": 0, "B": 0}, "missed-shots": {"A": 0, "B": 0}, "event": "start-game"}

    events = []
    i = 0

    # Sim events while fewer than max number of events, continue simming if tied
    while i < max_events or state["score"]["A"] == state["score"]["B"]:

        # initial possession (faceoff)
        if state["possession"] is None:
            rand_num = np.random.uniform(0, 1)

            if rand_num < ta_fo_per:
                current_team = "A"
                state["possession"] = "A"
            else:
                current_team = "B"
                state["possession"] = "B"

            current_event = "won-faceoff"
            state["event"] = "won-faceoff"

        else:
            current_team = state["possession"]
            current_event = state["event"]

        # Sim event based on transition probabiltiies
        if current_team == "A":
            data = team_A_probs.get(current_event)
            if data is None:
                break
        elif current_team == "B":
            data = team_B_probs.get(current_event)
            if data is None:
                break

        next_events, probs = data
        next_event = np.random.choice(next_events, p = probs)

        events.append((current_team, next_event))

        # Track team stats
        if next_event in ["goal", "shot-on-goal"]:
            state["shots"][current_team] += 1

        if next_event in ["goal", "shot-on-goal", "missed-shot", "blocked-shot"]:
            state["shot_attempts"][current_team] += 1

        if next_event == "penalty":
            state["penalties"][current_team] += 1

        if next_event == "stoppage":
            state["stoppages"][current_team] += 1

        if next_event == "hit":
            state["hits"][current_team] += 1

        if next_event == "blocked-shot":
            state["blocked-shots"][current_team] += 1

        if next_event == "missed-shot":
            state["missed-shots"][current_team] += 1

        # Handle faceoff after goal
        if next_event == "goal":
            state["score"][current_team] += 1

            rand_num = np.random.uniform(0, 1)

            if rand_num < ta_fo_per:
                state["possession"] = "A"
            else:
                state["possession"] = "B"

            state["event"] = "won-faceoff"
            i += 1
            continue

        # Handle possession switches
        if next_event in possession_switch_events:
            state["possession"] = "B" if current_team == "A" else "A"

        # otherwise possession stays the same
        state["event"] = next_event

        i += 1

    return state["score"], state["shots"], state["shot_attempts"], state["penalties"], state["stoppages"], state["hits"], state["blocked-shots"], state["missed-shots"], events

# Function to handle showing team logos
def display_logo(team, is_winner):
    st.empty()
    # If there is no winner yet, then no border
    border_style = "5px solid green" if is_winner else "none"
    
    with open(f"Team Logos/{team}.png", "rb") as f:
        img_bytes = f.read()
        encoded = base64.b64encode(img_bytes).decode()
    
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center;">
            <img src="data:image/png;base64,{encoded}"
                 style="border: {border_style}; border-radius: 10px; padding: 1px; width:300px;">
        </div>
        """,
        unsafe_allow_html = True
    )

st.title("NHL Simulator")

# Select simulation type
simulation_type_choice = st.selectbox("Select Simulation Type", options = simulation_types_df["simType"].unique(), index = None, 
                                      placeholder = "Select a simulation type...")

if simulation_type_choice:
    simulation_choice = simulation_types_df[simulation_types_df["simType"] == simulation_type_choice]["simType"].item()
    nGames = simulation_types_df[simulation_types_df["simType"] == simulation_type_choice]["nGames"].item()
    if "last_simulation_choice" not in st.session_state:
        st.session_state.last_simulation_choice = None

    if simulation_choice != st.session_state.last_simulation_choice:
        st.session_state.series_sim_has_run = False
        st.session_state.playoffs_sim_has_run = False
        st.session_state.last_simulation_choice = simulation_choice
else:
    # default
    simulation_choice = "Entire Playoffs"
    st.write("Please select a team to simulate.")

if (simulation_type_choice != "Entire Playoffs") & (simulation_type_choice != "1000 Playoffs"):
    # Select first team
    first_team_choice = st.selectbox("Select First Team", options = teams_df["fullName"].sort_values(ascending = True).unique(), index = None,
                                     placeholder = "Select a team...")

    if first_team_choice:
        first_team_df = teams_df[teams_df["fullName"] == first_team_choice]["fullName"].item()
        st.session_state.team1 = first_team_choice
        team1_abrv = teams_df[teams_df["fullName"] == first_team_choice]["triCode"].item()
        st.session_state.team1_id = teams_df[teams_df["fullName"] == first_team_choice]["id"].item()
    else:
        st.write("Please select a team to simulate.")

    # Select second team
    second_team_choice = st.selectbox("Select Second Team", options = teams_df["fullName"].sort_values(ascending = True).unique(), index = None, 
                                      placeholder = "Select a second team...")

    if second_team_choice:
        second_team_df = teams_df[teams_df["fullName"] == second_team_choice]["fullName"].item()
        st.session_state.team2 = second_team_choice
        team2_abrv = teams_df[teams_df["fullName"] == second_team_choice]["triCode"].item()
        st.session_state.team2_id = teams_df[teams_df["fullName"] == second_team_choice]["id"].item()

        # With both teams selected display logos
        col1, col2, col3 = st.columns(3)
        with col1:
            team1_placeholder = st.empty()
        with col2:
            st.markdown("<h3 style='text-align: center;'>vs</h3>", unsafe_allow_html = True, text_alignment = "center")
        with col3:
            team2_placeholder = st.empty()

        # Check if both teams have been selected before displaying logos
        try:
            team1_placeholder.image(f"Team Logos/{team1_abrv}.png")
            team2_placeholder.image(f"Team Logos/{team2_abrv}.png")
        except:
            st.write("## :red[Please ensure two teams are selected!]")

    else:
        st.write("Please select a team to simulate.")


if "series_sim_has_run" not in st.session_state:
    st.session_state.series_sim_has_run = False

if "playoffs_sim_has_run" not in st.session_state:
    st.session_state.playoffs_sim_has_run = False

if "playoffs1000_sim_has_run" not in st.session_state:
    st.session_state.playoffs1000_sim_has_run = False

if "scores" not in st.session_state:
    st.session_state.scores = [{"A":None, "B":None}] 

def simulate_round(matchups, team_maps, ta_fo_dict):
    winners = []
    losers = []
    scores = []
    series_scores = []
    series_games = []

    for teamA, teamB in matchups:
        team_A_map = team_maps[teamA]
        team_B_map = team_maps[teamB]

        ta_fo_per = ta_fo_dict[teamA]

        results = [simulate_game(team_A_map, team_B_map, ta_fo_per) for _ in range(7)]
        score = [r[0] for r in results]
        scores.append(score)

        team1_wins = 0
        team2_wins = 0
        team1_won = [True if s["A"] > s["B"]  else False for s in score]
        
        for g in range(7):
            if team1_wins < 4 and team2_wins < 4:
                if team1_won[g] == True:
                    team1_wins += 1
                else:
                    team2_wins += 1

        if team1_wins > team2_wins:
            winner = teamA
            loser = teamB
            series_score = f"{team1_wins}-{team2_wins}"
        elif team2_wins > team1_wins:
            winner = teamB
            loser = teamA
            series_score = f"{team2_wins}-{team1_wins}"

        winners.append(winner)
        losers.append(loser)
        series_scores.append(series_score)
        series_games.append(team1_wins + team2_wins)

    return winners, losers, series_scores, scores, series_games

# Run simulation button
if st.button("Run Simulation"):
    if simulation_choice == "One Game":
        st.session_state.series_sim_has_run = False
        st.session_state.playoffs_sim_has_run = False
        st.session_state.playoffs1000_sim_has_run = False
        team1_id = st.session_state.team1_id
        team2_id = st.session_state.team2_id
        team1 = st.session_state.team1
        team2 = st.session_state.team2

        # Filter for selected teams
        team_A_probs = team_transition_df[team_transition_df["id"] == team1_id]
        team_B_probs = team_transition_df[team_transition_df["id"] == team2_id]

        #Team faceoff percentages
        ta_fo_per = team_A_probs[(team_A_probs["typeDescKey"] == "goal") & (team_A_probs["next_event"] == "won-faceoff")]["prob"].item()

        team_A_map = build_transition_map(team_A_probs)
        team_B_map = build_transition_map(team_B_probs)
        
        # Simulate once
        results = [simulate_game(team_A_map, team_B_map, ta_fo_per) for _ in range(1)]
        scores = [r[0] for r in results]

        team1_wins = sum(1 for d in scores if d["A"] > d["B"])
        team2_wins = nGames - team1_wins

        team1_goals = scores[0]["A"]
        team2_goals = scores[0]["B"]

        if team1_goals > team2_goals:
            winner = team1_abrv
        elif team2_goals > team1_goals:
            winner = team2_abrv
 
        # Add border to logo off winning team with winner variable
        with team1_placeholder:
            display_logo(team1_abrv, team1_abrv == winner)
        with team2_placeholder:
            display_logo(team2_abrv, team2_abrv == winner)

        # Write who won
        if team1_wins > team2_wins:
            st.markdown(f"<h1 style='text-align: center;'>{team1} win {team1_goals}-{team2_goals}</h1>", unsafe_allow_html = True)
        elif team2_wins > team1_wins:
            st.markdown(f"<h1 style='text-align: center;'>{team2} win {team2_goals}-{team1_goals}</h1>", unsafe_allow_html = True)

        shots = [r[1] for r in results]
        shot_attempts = [r[2] for r in results]
        penalties = [r[3] for r in results]
        hits = [r[5] for r in results]
        blocked_shots = [r[6] for r in results]
        missed_shots = [r[7] for r in results]

        dat = {"": ["Score", "Shots", "Missed Shots", "Shot Attempts", "Hits", "Penalties", "Shots Blocked"], 
               team1: [scores[0]["A"], shots[0]["A"], missed_shots[0]["A"], shot_attempts[0]["A"], hits[0]["A"], penalties[0]["A"], blocked_shots[0]["B"]], 
               team2: [scores[0]["B"], shots[0]["B"], missed_shots[0]["B"], shot_attempts[0]["B"], hits[0]["A"], penalties[0]["A"], blocked_shots[0]["A"]]}
        st.dataframe(dat)

    elif simulation_choice == "One Series":
        st.session_state.series_sim_has_run = False
        st.session_state.playoffs_sim_has_run = False
        st.session_state.playoffs1000_sim_has_run = False
        team1_id = st.session_state.team1_id
        team2_id = st.session_state.team2_id

        team_A_probs = team_transition_df[team_transition_df["id"] == team1_id]
        team_B_probs = team_transition_df[team_transition_df["id"] == st.session_state.team2_id]

        ta_fo_per = team_A_probs[(team_A_probs["typeDescKey"] == "goal") & (team_A_probs["next_event"] == "won-faceoff")]["prob"].item()

        team_A_map = build_transition_map(team_A_probs)
        team_B_map = build_transition_map(team_B_probs)

        results = [simulate_game(team_A_map, team_B_map, ta_fo_per) for _ in range(7)]
        scores = [r[0] for r in results]

        team1_wins = 0
        team2_wins = 0
        team1_won = [True if score["A"] > score["B"]  else False for score in scores]
        
        for g in range(7):
            if team1_wins < 4 and team2_wins < 4:
                if team1_won[g] == True:
                    team1_wins += 1
                else:
                    team2_wins += 1

        series_games = team1_wins + team2_wins

        if team1_wins > team2_wins:
            winner = team1_abrv
        elif team2_wins > team1_wins:
            winner = team2_abrv
 
        # Add border to logo off winning team with winner variable
        with team1_placeholder:
            display_logo(team1_abrv, team1_abrv == winner)
        with team2_placeholder:
            display_logo(team2_abrv, team2_abrv == winner)

        if team1_wins > team2_wins:
            result_text = f"{st.session_state.team1} win the series {team1_wins}-{team2_wins}"
        elif team2_wins > team1_wins:
            result_text = f"{st.session_state.team2} win the series {team2_wins}-{team1_wins}"

        st.session_state.series_result = result_text

        shots = [r[1] for r in results]
        shot_attempts = [r[2] for r in results]
        penalties = [r[3] for r in results]
        hits = [r[5] for r in results]
        blocked_shots = [r[6] for r in results]
        missed_shots = [r[7] for r in results]

        # Add session wide metrics
        st.session_state.scores = scores
        st.session_state.shots = shots
        st.session_state.shot_attempts = shot_attempts
        st.session_state.penalties = penalties
        st.session_state.hits = hits
        st.session_state.blocked_shots = blocked_shots
        st.session_state.missed_shots = missed_shots
        st.session_state.series_games = series_games
        st.session_state.series_sim_has_run = True
        st.session_state.playoffs_sim_has_run = False
        st.session_state.playoffs1000_sim_has_run = False
        st.session_state.team1_wins = team1_wins
        st.session_state.team2_wins = team2_wins
        st.session_state.team1_abrv = team1_abrv
        st.session_state.team2_abrv = team2_abrv

    elif simulation_choice == "1000 Games":
        st.session_state.series_sim_has_run = False
        st.session_state.playoffs_sim_has_run = False
        st.session_state.playoffs1000_sim_has_run = False
        team1_id = st.session_state.team1_id
        team2_id = st.session_state.team2_id
        team1 = st.session_state.team1
        team2 = st.session_state.team2

        # Add comment about taking some time to sim
        please_wait_placeholder = st.empty()
        please_wait_placeholder.write("This may take a moment!")

        team_A_probs = team_transition_df[team_transition_df["id"] == team1_id]
        team_B_probs = team_transition_df[team_transition_df["id"] == team2_id]

        ta_fo_per = team_A_probs[(team_A_probs["typeDescKey"] == "goal") & (team_A_probs["next_event"] == "won-faceoff")]["prob"].item()

        team_A_map = build_transition_map(team_A_probs)
        team_B_map = build_transition_map(team_B_probs)

        results = [simulate_game(team_A_map, team_B_map, ta_fo_per) for _ in range(1000)]
        please_wait_placeholder.empty()
        scores = [r[0] for r in results]

        team1_wins = sum(1 for d in scores if d["A"] > d["B"])
        team2_wins = nGames - team1_wins

        if team1_wins > team2_wins:
            winner = team1_abrv
        elif team2_wins > team1_wins:
            winner = team2_abrv
 
        # Add border to logo off winning team with winner variable
        with team1_placeholder:
            display_logo(team1_abrv, team1_abrv == winner)
        with team2_placeholder:
            display_logo(team2_abrv, team2_abrv == winner)

        if team1_wins > team2_wins:
            st.markdown(f"<h1 style='text-align: center;'>{team1} win 1000 game series {team1_wins}-{team2_wins}</h1>", unsafe_allow_html = True)
        elif team2_wins > team1_wins:
            st.markdown(f"<h1 style='text-align: center;'>{team2} win 1000 game series {team2_wins}-{team1_wins}</h1>", unsafe_allow_html = True)

        shots = [r[1] for r in results]
        shot_attempts = [r[2] for r in results]
        penalties = [r[3] for r in results]
        hits = [r[5] for r in results]
        blocked_shots = [r[6] for r in results]
        missed_shots = [r[7] for r in results]

        avg_goals_A = np.mean([s["A"] for s in scores])
        avg_goals_B = np.mean([s["B"] for s in scores])

        avg_shots_A = np.mean([s["A"] for s in shots])
        avg_shots_B = np.mean([s["B"] for s in shots])

        avg_shot_attempts_A = np.mean([s["A"] for s in shot_attempts])
        avg_shot_attempts_B = np.mean([s["B"] for s in shot_attempts])

        avg_penalties_A = np.mean([s["A"] for s in penalties])
        avg_penalties_B = np.mean([s["B"] for s in penalties])

        avg_hits_A = np.mean([s["A"] for s in hits])
        avg_hits_B = np.mean([s["B"] for s in hits])

        avg_blocked_shots_A = np.mean([s["A"] for s in blocked_shots])
        avg_blocked_shots_B = np.mean([s["B"] for s in blocked_shots])

        avg_missed_shots_A = np.mean([s["A"] for s in missed_shots])
        avg_missed_shots_B = np.mean([s["B"] for s in missed_shots])

        dat = {"": ["Score", "Shots", "Missed Shots", "Shot Attempts", "Hits", "Penalties", "Shots Blocked"], 
               team1: [avg_goals_A, avg_shots_A, avg_missed_shots_A, avg_shot_attempts_A, avg_hits_A, avg_penalties_A, avg_blocked_shots_A], 
               team2: [avg_goals_B, avg_shots_B, avg_missed_shots_B, avg_shot_attempts_B, avg_hits_B, avg_penalties_B, avg_blocked_shots_B]}
        st.dataframe(dat)

    elif simulation_choice == "Entire Playoffs":
        st.session_state.series_sim_has_run = False
        st.session_state.playoffs_sim_has_run = True
        st.session_state.playoffs1000_sim_has_run = False

        # Setup intial matchups
        teams = ["CAR", "OTT", "PIT", "PHI", "BUF", "BOS", "TBL", "MTL", "COL", "LAK", "DAL", "MIN", "VGK", "UTA", "EDM", "ANA"]
        placements = ["M1", "WC2", "M2", "M3", "A1", "WC1", "A2", "A3", "C1", "WC2", "C2", "C3", "P1", "WC1", "P2", "P3"]
        placements_teams = [team + f" ({placement})" for placement, team in zip(placements, teams)]

        round1 = [(teams[0], teams[1]), (teams[2], teams[3]), (teams[4], teams[5]), (teams[6], teams[7]), (teams[8], teams[9]), (teams[10], teams[11]), 
                  (teams[12], teams[13]), (teams[14], teams[15])]
        
        team_maps = {}
        ta_fo_dict = {}
        for matchup in round1:
            team_A_probs = team_transition_df[team_transition_df["id"] == teams_df[teams_df["triCode"] == matchup[0]]["id"].item()]
            team_B_probs = team_transition_df[team_transition_df["id"] == teams_df[teams_df["triCode"] == matchup[1]]["id"].item()]

            team_maps[matchup[0]] = build_transition_map(team_A_probs)
            team_maps[matchup[1]] = build_transition_map(team_B_probs)

            ta_fo_dict[matchup[0]] = team_A_probs[(team_A_probs["typeDescKey"] == "goal") & (team_A_probs["next_event"] == "won-faceoff")]["prob"].item()

            ta_fo_dict[matchup[1]] = team_B_probs[(team_B_probs["typeDescKey"] == "goal") & (team_B_probs["next_event"] == "won-faceoff")]["prob"].item()

        series_dfs = []
        # Round 1 Results
        r1_winners, r1_losers, r1_series_score, r1_scores, r1_games = simulate_round(round1, team_maps, ta_fo_dict)
        r1_results = ["R1: " + placements_teams[teams.index(winner)] + " defeats " + placements_teams[teams.index(loser)] + f" {score}" for winner, loser, score in zip(r1_winners, r1_losers, r1_series_score)]

        round1_dfs = []
        for game in range(len(r1_winners)):
            temp_df = pd.DataFrame(r1_scores[game][: r1_games[game]]).reset_index()
            temp_df = temp_df.rename(columns = {"index": "Game", "A": round1[game][0], "B": round1[game][1]})
            temp_df["Game"] = temp_df["Game"] + 1
            round1_dfs.append(temp_df)

        # Round 2 Results
        round2 = [(r1_winners[0], r1_winners[1]), (r1_winners[2], r1_winners[3]), (r1_winners[4], r1_winners[5]), (r1_winners[6], r1_winners[7])]
        r2_winners, r2_losers, r2_series_score, r2_scores, r2_games = simulate_round(round2, team_maps, ta_fo_dict)
        r2_results = ["R2: " + placements_teams[teams.index(winner)] + " defeats " + placements_teams[teams.index(loser)] + f" {score}" for winner, loser, score in zip(r2_winners, r2_losers, r2_series_score)]

        round2_dfs = []
        for game in range(len(r2_winners)):
            temp_df = pd.DataFrame(r2_scores[game][: r2_games[game]]).reset_index()
            temp_df = temp_df.rename(columns = {"index": "Game", "A": round2[game][0], "B": round2[game][1]})
            temp_df["Game"] = temp_df["Game"] + 1
            round2_dfs.append(temp_df)

        # Round 3 Results
        round3 = [(r2_winners[0], r2_winners[1]), (r2_winners[2], r2_winners[3])]
        r3_winners, r3_losers, r3_series_score, r3_scores, r3_games = simulate_round(round3, team_maps, ta_fo_dict)
        r3_results = ["CF: " + placements_teams[teams.index(winner)] + " defeats " + placements_teams[teams.index(loser)] + f" {score}" for winner, loser, score in zip(r3_winners, r3_losers, r3_series_score)]

        round3_dfs = []
        for game in range(len(r3_winners)):
            temp_df = pd.DataFrame(r3_scores[game][: r3_games[game]]).reset_index()
            temp_df = temp_df.rename(columns = {"index": "Game", "A": round3[game][0], "B": round3[game][1]})
            temp_df["Game"] = temp_df["Game"] + 1
            round3_dfs.append(temp_df)

        # Round 4 Results
        round4 = [(r3_winners[0], r3_winners[1])]
        r4_winners, r4_losers, r4_series_score, r4_scores, r4_games = simulate_round(round4, team_maps, ta_fo_dict)
        r4_results = ["SCF: " + placements_teams[teams.index(winner)] + " defeats " + placements_teams[teams.index(loser)] + f" {score}" for winner, loser, score in zip(r4_winners, r4_losers, r4_series_score)]
        series_results_options = r1_results + r2_results + r3_results + r4_results

        round4_dfs = []
        round4_df = pd.DataFrame(r4_scores[0][: r4_games[0]]).reset_index()
        round4_df = round4_df.rename(columns = {"index": "Game", "A": round4[0][0], "B": round4[0][1]})
        round4_df["Game"] = round4_df["Game"] + 1
        round4_dfs.append(round4_df)

        series_dfs = round1_dfs + round2_dfs + round3_dfs + round4_dfs

        series_results_options.reverse()
        series_dfs.reverse()

        st.session_state.series_results_options = series_results_options
        st.session_state.series_dfs = series_dfs
        st.session_state.champ = r4_winners
    
    elif simulation_choice == "1000 Playoffs":
        st.session_state.series_sim_has_run = False
        st.session_state.playoffs_sim_has_run = False
        st.session_state.playoffs1000_sim_has_run = True
        please_wait_placeholder = st.empty()
        please_wait_placeholder.write("This will take a few minutes, perfect time to grab a snack!")

        teams = ["CAR", "OTT", "PIT", "PHI", "BUF", "BOS", "TBL", "MTL", "COL", "LAK", "DAL", "MIN", "VGK", "UTA", "EDM", "ANA"]
        placements = ["M1", "WC2", "M2", "M3", "A1", "WC1", "A2", "A3", "C1", "WC2", "C2", "C3", "P1", "WC1", "P2", "P3"]
        placements_teams = [team + f" ({placement})" for placement, team in zip(placements, teams)]

        round1 = [(teams[0], teams[1]), (teams[2], teams[3]), (teams[4], teams[5]), (teams[6], teams[7]), (teams[8], teams[9]), (teams[10], teams[11]), 
                  (teams[12], teams[13]), (teams[14], teams[15])]
        
        team_maps = {}
        ta_fo_dict = {}
        for matchup in round1:
            team_A_probs = team_transition_df[team_transition_df["id"] == teams_df[teams_df["triCode"] == matchup[0]]["id"].item()]
            team_B_probs = team_transition_df[team_transition_df["id"] == teams_df[teams_df["triCode"] == matchup[1]]["id"].item()]

            team_maps[matchup[0]] = build_transition_map(team_A_probs)
            team_maps[matchup[1]] = build_transition_map(team_B_probs)

            ta_fo_dict[matchup[0]] = team_A_probs[(team_A_probs["typeDescKey"] == "goal") & (team_A_probs["next_event"] == "won-faceoff")]["prob"].item()

            ta_fo_dict[matchup[1]] = team_B_probs[(team_B_probs["typeDescKey"] == "goal") & (team_B_probs["next_event"] == "won-faceoff")]["prob"].item()

        all_r1_winners = []
        all_r2_winners = []
        all_r3_winners = []
        all_r4_winners = []
        for i in range(1000):
            # Round 1 Results
            r1_winners, r1_losers, r1_series_score, r1_scores, r1_games = simulate_round(round1, team_maps, ta_fo_dict)
            all_r1_winners.append(r1_winners)

            # Round 2 Results
            round2 = [(r1_winners[0], r1_winners[1]), (r1_winners[2], r1_winners[3]), (r1_winners[4], r1_winners[5]), (r1_winners[6], r1_winners[7])]
            r2_winners, r2_losers, r2_series_score, r2_scores, r2_games = simulate_round(round2, team_maps, ta_fo_dict)
            all_r2_winners.append(r2_winners)

            # Round 3 Results
            round3 = [(r2_winners[0], r2_winners[1]), (r2_winners[2], r2_winners[3])]
            r3_winners, r3_losers, r3_series_score, r3_scores, r3_games = simulate_round(round3, team_maps, ta_fo_dict)
            all_r3_winners.append(r3_winners)

            # Round 4 Results
            round4 = [(r3_winners[0], r3_winners[1])]
            r4_winners, r4_losers, r4_series_score, r4_scores, r4_games = simulate_round(round4, team_maps, ta_fo_dict)
            all_r4_winners.append(r4_winners)

        # Clear placeholder after simulation complete
        please_wait_placeholder.empty()

        r1_winners_list = [item for all_winners in all_r1_winners for item in all_winners]
        r2_winners_list = [item for all_winners in all_r2_winners for item in all_winners]
        r3_winners_list = [item for all_winners in all_r3_winners for item in all_winners]
        r4_winners_list = [item for all_winners in all_r4_winners for item in all_winners]

        r1_winner_counts = pd.Series(r1_winners_list).value_counts()
        r1_probs = (r1_winner_counts / 1000) * 100
        r1_probs = r1_probs.reset_index()
        r1_probs = r1_probs.rename(columns = {"index": "Team", "count": "Win First Round"})

        r2_winner_counts = pd.Series(r2_winners_list).value_counts()
        r2_probs = (r2_winner_counts / 1000) * 100
        r2_probs = r2_probs.reset_index()
        r2_probs = r2_probs.rename(columns = {"index": "Team", "count": "Win Second Round"})

        r3_winner_counts = pd.Series(r3_winners_list).value_counts()
        r3_probs = (r3_winner_counts / 1000) * 100
        r3_probs = r3_probs.reset_index()
        r3_probs = r3_probs.rename(columns = {"index": "Team", "count": "Win Conference Final"})

        r4_winner_counts = pd.Series(r4_winners_list).value_counts()
        r4_probs = (r4_winner_counts / 1000) * 100
        r4_probs = r4_probs.reset_index()
        r4_probs = r4_probs.rename(columns = {"index": "Team", "count": "Win Stanley Cup"})

        playoff_teams_df = teams_df[teams_df["triCode"].isin(teams)]
        playoff_results_df = (playoff_teams_df[["fullName", "triCode"]].merge(r1_probs, left_on = "triCode", right_on = "Team", how = "outer")[["fullName", "Win First Round", "triCode"]]
              .merge(r2_probs, left_on = "triCode", right_on = "Team", how = "outer")[["fullName", "Win First Round", "Win Second Round", "triCode"]]
              .merge(r3_probs, left_on = "triCode", right_on = "Team", how = "outer")[["fullName", "Win First Round", "Win Second Round", "Win Conference Final", "triCode"]]
              .merge(r4_probs, left_on = "triCode", right_on = "Team", how = "outer")[["fullName", "Win Stanley Cup", "Win Conference Final", "Win Second Round",  "Win First Round"]])
        playoff_results_df = playoff_results_df.fillna(0)
        playoff_results_df = playoff_results_df.sort_values(by = "Win Stanley Cup", ascending = False)
        playoff_results_df = playoff_results_df.reset_index(drop = True)
        playoff_results_df.index += 1
        playoff_results_df = playoff_results_df.rename(columns = {"fullName": "Team"})
        st.table(playoff_results_df)

        


if "series_result" in st.session_state and st.session_state.series_sim_has_run:
    st.markdown(
        f"<h1 style='text-align: center;'>{st.session_state.series_result}</h1>",
        unsafe_allow_html=True
    )

if simulation_choice == "One Series" and st.session_state.series_sim_has_run:

    scores = st.session_state.scores
    shots = st.session_state.shots
    shot_attempts = st.session_state.shot_attempts
    penalties = st.session_state.penalties
    hits = st.session_state.hits
    blocked_shots = st.session_state.blocked_shots
    missed_shots = st.session_state.missed_shots
    series_games = st.session_state.series_games
    team1_wins = st.session_state.team1_wins
    team2_wins = st.session_state.team2_wins
    team1_abrv = st.session_state.team1_abrv
    team2_abrv = st.session_state.team2_abrv


    if team1_wins > team2_wins:
        winner = team1_abrv
    elif team2_wins > team1_wins:
        winner = team2_abrv
 
    # Add border to logo off winning team with winner variable
    with team1_placeholder:
        display_logo(team1_abrv, team1_abrv == winner)
    with team2_placeholder:
        display_logo(team2_abrv, team2_abrv == winner)

    series_games_options = [f"Game {g+1}" for g in range(series_games)]

    game_choice = st.selectbox("Select Game Number", options = series_games_options, index = 0)

    selected_game = int(game_choice[-1]) - 1

    st.write(f"{game_choice} Statistics")

    dat = {"": ["Score", "Shots", "Missed Shots", "Shot Attempts", "Hits", "Penalties", "Shots Blocked"], 
           st.session_state.team1: [scores[selected_game]["A"], shots[selected_game]["A"], missed_shots[selected_game]["A"], shot_attempts[selected_game]["A"],
                                    hits[selected_game]["A"], penalties[selected_game]["A"], blocked_shots[selected_game]["B"]],
           st.session_state.team2: [scores[selected_game]["B"], shots[selected_game]["B"], missed_shots[selected_game]["B"], shot_attempts[selected_game]["B"],
                                    hits[selected_game]["B"], penalties[selected_game]["B"], blocked_shots[selected_game]["A"]]}

    st.dataframe(dat)

elif simulation_choice == "Entire Playoffs" and st.session_state.playoffs_sim_has_run:
    series_results_options = st.session_state.series_results_options
    series_dfs = st.session_state.series_dfs
    champ = st.session_state.champ[0]

    team_name = teams_df[teams_df["triCode"] == champ]["fullName"]

    st.markdown(f"<h1 style='text-align: center;'>The {team_name.item()} are your Stanley Cup champions!</h1>", unsafe_allow_html = True)

    display_logo(champ, True)

    series_choice = st.selectbox("Select Game Number", options = series_results_options, index = 0)

    game_ind = series_results_options.index(series_choice)
    st.dataframe(series_dfs[game_ind], hide_index = True)