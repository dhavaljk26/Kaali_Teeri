from threading import Lock

lifetime_scores = {"Player Name" : "Total Points"}
scorecard_lock = Lock()

def add_fixed_scores_from_current_game(points, player_list):
    for player in player_list:
        if lifetime_scores.get(player) == None:
            lifetime_scores.update({player : points})
        else:
            lifetime_scores.update({player : lifetime_scores.get(player) + points })

def add_player_to_db(player):
    if lifetime_scores.get(player) == None:
        lifetime_scores.update({player: 0.0 })    