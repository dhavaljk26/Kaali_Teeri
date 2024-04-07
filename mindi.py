from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
import random
from .scorecard import *
from .models import Card, GameOfMindi, Hand, Round


team_1 = []
team_2 = []
players = []
cards = []
hands = []
rounds = []
past_rounds = []
game = GameOfMindi()
game_started = False
player_order = []
player_shift = 0
player_points = {}
removed_card_set = []
mindi_played_list_1 = []
mindi_played_list_2 = []

rank = {}
for i in range(2,11):
	rank[str(i)] = i-1
rank['J'] = 11
rank['Q'] = 12
rank['K'] = 13
rank['A'] = 14

mindi = Blueprint('mindi', __name__, url_prefix='/mindi')


@mindi.route('/players')
@login_required
def list_players():

	global team_1, team_2

	present_in_1 = any([player==current_user.name for player in team_1])
	present_in_2 = any([player==current_user.name for player in team_2])
	present = present_in_1 or present_in_2
	return render_template('mindi/players.html', team_1=team_1, team_2=team_2, present=present, present1=present_in_1, present2=present_in_2)


@mindi.route('/add_me/<team>')
@login_required
def add_player(team):
	global game_started, players
	if game_started == True:
		flash('Game Started wait for game to finish')
		return redirect(url_for('mindi.list_players'))

	print("value is ", team)
	
	present_in_1 = any([player==current_user.name for player in team_1])
	present_in_2 = any([player==current_user.name for player in team_2])
	if(present_in_2):
		team_2.remove(current_user.name)
	elif(present_in_1):
		team_1.remove(current_user.name)

	if(team == "1"):
		team_1.append(current_user.name)
	else:
		team_2.append(current_user.name)

	add_player_to_db(current_user.name)
	return redirect(url_for('mindi.list_players'))


@mindi.route('/start_game')
@login_required
def start_game():
	global game_started, team_1, team_2
	if len(team_1) == len(team_2):
		if game_started == False:
			game_started = True
			distribute_cards()
			setup_game()
			return redirect(url_for('mindi.play_round', round_id=1))
		else:
			return render_template('mindi/message_popup.html')
	else:
		return render_template('mindi/message_popup.html')


@mindi.route('/game_query')
@login_required
def game_query():
	global game_started, team_1, team_2
	present = any([player==current_user.name for player in team_1]) or any([player==current_user.name for player in team_2])
	if present:
		return str(game_started)
	else:
		return False

@mindi.route('/next_turn/<int:previos_player>/<int:round_id>')
@login_required
def check_next_turn(previos_player, round_id):
	global player_shift, rounds, players
	if round_id > len(rounds):
		return redirect(url_for('mindi.end_game', round_id=round_id))
	return str(player_shift != previos_player or len(players)==len(rounds[round_id-1].cards))

@mindi.route('/round/<int:round_id>')
@login_required
def play_round(round_id):
	global team_1, team_2, mindi_played_list_1, mindi_played_list_2 ,player_order, player_shift, game, rounds, cards, players, past_rounds, player_points

	team1 = game.team1
	hand = get_hand()

	table_cards = get_round(round_id)
	mindi_played_list = []

	if len(player_order) <= player_shift:
		past_rounds.insert(0,table_cards)
		winner = 0
		start_suit = table_cards[0].suit
		for i, card in enumerate(table_cards):
			if card.suit==start_suit and rank[card.value] >= rank[table_cards[winner].value]:
				winner = i
			if rank[card.value] == 9: # This means, its a mindi
				mindi_played_list.append(card.suit)

		flag = 0
		
		for i, card in enumerate(table_cards):
			if card.suit != start_suit:
				if game.trump == "":
					game.trump = card.suit
				if card.suit == game.trump and (flag==0 or rank[card.value] >= rank[table_cards[winner].value]):
					winner = i
					flag=1

		rounds[round_id-1].winner = player_order[winner]
		rounds[round_id-1].points = sum(i.points for i in table_cards)
		player_points[rounds[round_id-1].winner] += rounds[round_id-1].points
		number_of_rounds = len(cards)/len(players)

		if len(mindi_played_list) > 0:
			winnerTeam = any([player==rounds[round_id-1].winner for player in team_1])
			if winnerTeam == True:
				mindi_played_list_1.extend(mindi_played_list)
			else:
				mindi_played_list_2.extend(mindi_played_list)

		if round_id >= number_of_rounds:
			return redirect(url_for('mindi.display_results'))

		rounds.append(Round(starting_player=player_order[winner], cards=[]))
		player_shift = 0
		get_order(round_id+1)

	if len(player_order)==len(rounds[round_id-1].cards):
		return redirect(url_for('mindi.play_round', round_id=round_id+1))

	activityClass = "" if current_user.name == player_order[player_shift] else "inactiveLink"

	suit_exists = False
	if len(table_cards) > 0:
		truth_array = [i.suit==table_cards[0].suit for i in hand.cards]
		suit_exists = any(truth_array)

	team_2_score = 0
	team_1_score = 0
	for player in team_2:
		team_2_score += player_points[player]
	for player in team_1:
		team_1_score += player_points[player]

	return render_template('mindi/round.html', round_id=round_id, cards=sorted(hand.cards, key=lambda x:(x.suit, x.value)), trump=game.trump, table_cards=table_cards, activityClass=activityClass, turn_id=player_shift, past_rounds=past_rounds, player_order=player_order, team_1_score=team_1_score, team_2_score=team_2_score, player_points=player_points, suit_exists=suit_exists, lifetime_scores=lifetime_scores_mindi, partner_names=team1, mindi_team_1=mindi_played_list_1, mindi_team_2=mindi_played_list_2)

@mindi.route('/make_move/<string:suit>/<string:value>/<int:round_id>')
@login_required
def make_move(suit, value, round_id):
	global player_shift, player_order, rounds, hands, game, cards

	hand = get_hand()

	card = [card for card in cards if (card.suit==suit and card.value==value)][0]

	used_card_index = [i for i, card in enumerate(hand.cards) if (card.suit==suit and card.value==value)]

	if len(used_card_index)==0 or current_user.name != player_order[player_shift]:
		return redirect(url_for('mindi.play_round', round_id=round_id))

	else:
		used_card_index = used_card_index[0]

	rounds[round_id-1].cards.append(card)
	player_shift += 1

	hand.cards.pop(used_card_index)

	return redirect(url_for('mindi.play_round', round_id=round_id))

@mindi.route('/display_results')
@login_required
def display_results():
	global players, rounds, game
	player_points = {i:0 for i in players}
	for round in rounds:
		player_points[round.winner] += round.points

	team_bidder=0
	team_bidder2=0
	for player in game.team1:
		team_bidder += player_points[player]

	for player in game.team2:
		team_bidder2 += player_points[player]

	message = "Team 1 " + str(team_1) + " got " + str(team_bidder) + " points! \n Team 2 " + str(team_2) + " got " + str(team_bidder2) + " points!"

	if team_bidder > team_bidder2:
		winner_message = "Team 1 Won!"
	else:
		winner_message = "Team 2 Won!"

	return render_template("display_results.html", message=message, winner_message=winner_message, player_points=player_points)

@mindi.route('/end_game')
@login_required
def end_game():
	scorecard_lock.acquire()
	try:
		global players, removed_card_set, mindi_played_list_1, mindi_played_list_2, team_1, team_2, cards, hands,  rounds, game, game_started, player_order, past_rounds, player_shift, player_points
		factor = 0
		if game_started == False:
			scorecard_lock.release()
			return redirect(url_for('mindi.list_players'))

		url_params = request.args
		game_winner = url_params.get('winner','')
		print(game_winner)
	
		try:
			if (game_winner == "1"):
				add_fixed_scores_from_current_game_of_mindi(team_1)
			elif(game_winner == "2"):
				add_fixed_scores_from_current_game_of_mindi(team_2)
			elif (game_winner == "draw"):
				factor = 0
			else:
				scorecard_lock.release()
				return render_template('mindi/end_game_popup.html')

		except Exception as error:
			print("Scores already added:", error)


		del players[:]
		del cards[:]
		del hands[:]
		del rounds[:]
		del mindi_played_list_1[:]
		del mindi_played_list_2[:]
		del removed_card_set[:]
		del team_1[:], team_2[:]
		player_points = {}
		game = GameOfMindi()
		game_started = False
		del player_order[:]
		del past_rounds[:]
		player_shift = 0
		scorecard_lock.release()
		return redirect(url_for('mindi.list_players'))
	except Exception as error:
		scorecard_lock.release()
		return render_template('mindi/end_game_popup.html')


def setup_game():
	global player_order, team_1, team_2,game, player_shift, rounds, player_points
	game.team2 = team_2
	game.team1 = team_1
	player_shift = 0
	for index in range(len(team_1)):
		player_order.append(team_1[index])
		player_order.append(team_2[index])
		player_points[team_1[index]] = 0
		player_points[team_2[index]] = 0

	rounds.append(Round(starting_player=player_order[player_shift], cards=[]))


def create_deck(number_of_decks, number_of_players):
	global cards, removed_card_set

	cards = []

	number_of_removed_cards = (number_of_decks*52)%(number_of_players)

	suits = ['spades', 'diams', 'clubs', 'hearts']

	values = ['A', '2', '3','4','5','6','7','8','9','10', 'J', 'Q', 'K']

	points = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1000, 1, 1, 1]

	for i in range(number_of_decks):
		for suit in suits:
			for point_index,value in enumerate(values):
				card = Card(suit = suit, value = value, points = points[point_index])
				if value == '2' and number_of_removed_cards > 0:
					number_of_removed_cards -= 1
					removed_card_set.append(card)
					continue
				else:
					cards.append(card)

def get_hand():
	global hands
	hand = [i for i in hands if i.player == current_user.name][0]
	return hand

def get_round(round_id):
	global rounds
	return rounds[round_id-1].cards

def get_order(round_id):
	global player_order, rounds

	start_index = player_order.index(rounds[round_id-1].starting_player)
	temp1 = player_order[start_index:]
	temp1.extend(player_order[:start_index])
	player_order = temp1

def distribute_cards():
	global players, cards, hands, team_1, team_2

	for player in team_1:
		players.append(player)
	for player in team_2:
		players.append(player)

	number_of_players = len(players)

	if number_of_players > 4:
		create_deck(2, number_of_players)
	else:
		create_deck(1, number_of_players)

	random.shuffle(cards)

	number_of_cards = len(cards)

	number_of_cards_in_hand = int(number_of_cards / number_of_players)

	distributed = 0

	for i in range(number_of_players):
		hands.append(Hand(player=players[i], cards=cards[distributed:distributed+number_of_cards_in_hand]))
		distributed += number_of_cards_in_hand