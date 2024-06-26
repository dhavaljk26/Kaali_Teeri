from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
import random
from .scorecard import *
from .models import Card, Game, Hand, Partner, Round


players = []
cards = []
hands = []
bidders = []
rounds = []
past_rounds = []
game = Game()
game_started = False
bidding_completed = False
bid_winner = ""
bid_winner_index = 0
partner_chosen = False
player_order = []
player_shift = 0
player_points = {}

rank = {}
for i in range(2,11):
	rank[str(i)] = i-1
rank['J'] = 11
rank['Q'] = 12
rank['K'] = 13
rank['A'] = 14

app_game = Blueprint('app_game', __name__)


@app_game.route('/players')
@login_required
def list_players():

	global players

	present = any([player==current_user.name for player in players])

	return render_template('players.html', players=players, present=present)


@app_game.route('/add_me')
@login_required
def add_player():
	global game_started, players
	if game_started == True:
		flash('Game Started wait for game to finish')
		return redirect(url_for('app_game.list_players'))

	players.append(current_user.name)
	add_player_to_db(current_user.name)
	return redirect(url_for('app_game.list_players'))


@app_game.route('/game_query')
@login_required
def game_query():
	global game_started
	return str(game_started)


@app_game.route('/start_game')
@login_required
def start_game():
	global game_started
	if game_started == False:
		game_started = True
		distribute_cards()
	return redirect(url_for('app_game.bid'))

def create_deck(number_of_decks, number_of_players):
	global cards

	cards = []

	number_of_removed_cards = (number_of_decks*52)%(number_of_players)

	suits = ['spades', 'diams', 'clubs', 'hearts']

	values = ['A', '2', '3','4','5','6','7','8','9','10', 'J', 'Q', 'K']

	points = [10, 0, 0, 0, 5, 0, 0, 0, 0, 10, 10, 10, 10]

	for i in range(number_of_decks):
		for suit in suits:
			for point_index,value in enumerate(values):
				if value == '3' and suit == 'spades':
					card = Card(suit = suit, value = value, points = 30)
					cards.append(card)
				elif value == '2' and number_of_removed_cards > 0:
					number_of_removed_cards -= 1
					continue
				else:
					card = Card(suit = suit, value = value, points = points[point_index])
					cards.append(card)


def distribute_cards():
	global players, cards, hands

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


def get_hand():
	global hands
	hand = [i for i in hands if i.player == current_user.name][0]
	return hand

def get_round(round_id):
	global rounds
	return rounds[round_id-1].cards

@app_game.route('/bid')
@login_required
def bid():
	global players, bidders
	already_bid = current_user.name in bidders
	hand = get_hand()
	return render_template('bid.html', already_bid=already_bid, cards=sorted(hand.cards, key=lambda x:(x.suit, x.value)), activityClass="inactiveLink")

@app_game.route('/bid', methods=['POST'])
@login_required
def bid_post():

	global bidders, players, game, bidding_completed

	if bidding_completed == False:
		hand = get_hand()
		if current_user.name in bidders == True:
			return render_template('bid.html', already_bid=(current_user.name in bidders), cards=sorted(hand.cards, key=lambda x:(x.suit, x.value)))
		bid_points = int(request.form.get('bid'))

		if bid_points == -1:
			number_of_players = len(players)
			bid_points = 150 if number_of_players <= 4 else 270

		if game.bidder=="" or game.bid < bid_points:
			game.bid = bid_points
			game.bidder = current_user.name

		bidders.append(current_user.name)

		return render_template('bid.html', already_bid=True, cards=sorted(hand.cards, key=lambda x:(x.suit, x.value)), activityClass="inactiveLink")

	else:

		return render_template('404.html')


@app_game.route('/bidding_completed')
@login_required
def check_bidding_completed():
	global bidding_completed
	if bidding_completed==True:
		return str(True)
	else:
		if sorted(players) == sorted(bidders):
			bidding_completed = True
			return str(True)
		else:
			return str(False)


@app_game.route('/trump_and_partner')
@login_required
def choose_trump_and_partner():
	global game, players

	number_of_players = len(players)
	number_of_partners = int(number_of_players/2)-1
	suits = ['spades', 'diams', 'clubs', 'hearts']
	values = ['A', '2', '3','4','5','6','7','8','9','10', 'J', 'Q', 'K']
	turn = [1] if number_of_players <= 4 else [1,2]
	to_choose = False
	if game.bidder == current_user.name:
		to_choose = True
	hand = get_hand()
	return render_template('/choose.html', to_choose=to_choose, suits=suits, values=values, turn=turn, number_of_partners=number_of_partners, cards=sorted(hand.cards, key=lambda x:(x.suit, x.value)), activityClass="inactiveLink")


@app_game.route('/trump_and_partner', methods=['POST'])
@login_required
def post_choose_trump_and_partner():
	global partner_chosen, player_order, game, players, rounds, player_points

	trump = request.form.get('trump')
	game.trump = trump

	number_of_players = len(players)
	number_of_partners = int(number_of_players/2) - 1

	for i in range(1, number_of_partners+1):
		game.partners.append(Partner(suit=request.form.get('partner_suit'+str(i)), value=request.form.get('partner_value'+str(i)), turn_number=int(request.form.get('partner_turn'+str(i)))))

	partner_chosen = True
	for player in players:
		player_order.append(player)

	bidder = game.bidder
	bidder_index = player_order.index(bidder)

	temp1 = player_order[bidder_index:]
	temp1.extend(player_order[:bidder_index])

	player_order = temp1
	global bid_winner, bid_winner_index
	bid_winner = bidder
	bid_winner_index = bidder_index
	rounds.append(Round(starting_player=bidder, cards=[]))

	for i in players:
		player_points[i] = 0

	return redirect(url_for('app_game.play_round', round_id=1))

@app_game.route('/check_selection')
@login_required
def check_selection():
	global partner_chosen
	return str(partner_chosen)

@app_game.route('/round/<int:round_id>')
@login_required
def play_round(round_id):
	global player_order, player_shift, game, rounds, cards, players, past_rounds, bid_winner, player_points

	partners = game.partners
	partner_cards = []
	for partner in partners:
		partner_cards.append((partner.suit, partner.value, partner.turn_number))

	hand = get_hand()

	table_cards = get_round(round_id)

	if len(player_order) <= player_shift:
		past_rounds.insert(0,table_cards)
		winner = 0
		start_suit = table_cards[0].suit
		for i, card in enumerate(table_cards):
			if card.suit==start_suit and rank[card.value] >= rank[table_cards[winner].value]:
				winner = i
		flag = 0
		for i, card in enumerate(table_cards):
			if card.suit == game.trump and (flag==0 or rank[card.value] >= rank[table_cards[winner].value]):
				winner = i
				flag=1

		rounds[round_id-1].winner = player_order[winner]
		rounds[round_id-1].points = sum(i.points for i in table_cards)
		player_points[rounds[round_id-1].winner] += rounds[round_id-1].points
		number_of_rounds = len(cards)/len(players)

		if round_id >= number_of_rounds:
			return redirect(url_for('app_game.display_results'))

		rounds.append(Round(starting_player=player_order[winner], cards=[]))
		player_shift = 0
		get_order(round_id+1)

	if len(player_order)==len(rounds[round_id-1].cards):
		return redirect(url_for('app_game.play_round', round_id=round_id+1))

	activityClass = "" if current_user.name == player_order[player_shift] else "inactiveLink"

	suit_exists = False
	if len(table_cards) > 0:
		truth_array = [i.suit==table_cards[0].suit for i in hand.cards]
		suit_exists = any(truth_array)

	partner_names = [i.player for i in game.partners]
	partner_names.append(game.bidder)
	return render_template('round.html', round_id=round_id, cards=sorted(hand.cards, key=lambda x:(x.suit, x.value)), trump=game.trump, partner_cards=partner_cards, table_cards=table_cards, activityClass=activityClass, turn_id=player_shift, past_rounds=past_rounds, player_order=player_order, bid_winner= bid_winner, bid=game.bid, player_points=player_points, suit_exists=suit_exists, lifetime_scores=lifetime_scores, partner_names=partner_names)

def get_order(round_id):
	global player_order, rounds

	start_index = player_order.index(rounds[round_id-1].starting_player)
	temp1 = player_order[start_index:]
	temp1.extend(player_order[:start_index])
	player_order = temp1

@app_game.route('/make_move/<string:suit>/<string:value>/<int:round_id>')
@login_required
def make_move(suit, value, round_id):
	global player_shift, player_order, rounds, hands, game, cards

	hand = get_hand()

	card = [card for card in cards if (card.suit==suit and card.value==value)][0]

	used_card_index = [i for i, card in enumerate(hand.cards) if (card.suit==suit and card.value==value)]

	if len(used_card_index)==0 or current_user.name != player_order[player_shift]:
		return redirect(url_for('app_game.play_round', round_id=round_id))

	else:
		used_card_index = used_card_index[0]

	rounds[round_id-1].cards.append(card)
	table_cards = get_round(round_id)
	player_shift += 1

	hand.cards.pop(used_card_index)

	partner_i = [i for i in game.partners if (i.suit==suit and i.value==value)]

	count = 0
	if len(partner_i)!=0:
		for round in rounds:
			for card in round.cards:
				if card.suit==suit and card.value==value:
					count+=1

	for partner in partner_i:
		if partner.turn_number == count:
			partner.player = current_user.name

	return redirect(url_for('app_game.play_round', round_id=round_id))

@app_game.route('/next_turn/<int:previos_player>/<int:round_id>')
@login_required
def check_next_turn(previos_player, round_id):
	global player_shift, rounds, players
	if round_id > len(rounds):
		return redirect(url_for('app_game.end_game', round_id=round_id))
	return str(player_shift != previos_player or len(players)==len(rounds[round_id-1].cards))

@app_game.route('/end_game')
@login_required
def end_game():
	scorecard_lock.acquire()
	try:
		global players, cards, hands, bidders, rounds, game, game_started, bidding_completed, partner_chosen, player_order, bid_winner, past_rounds, player_shift, bid_winner_index, player_points
		factor = 0
		if game_started == False:
			scorecard_lock.release()
			return redirect(url_for('app_game.list_players'))

		url_params = request.args
		game_winner = url_params.get('winner','')
		print(game_winner)
		if (game_winner == "p"):
			factor = 2
		elif (game_winner == "np"):
			factor = -2
		elif (game_winner == "draw"):
			factor = 0
		else:
			scorecard_lock.release()
			return render_template('end_game_popup.html')

		try:
			partner_found = set()
			partner_found.add(players[bid_winner_index])
			add_fixed_scores_from_current_game(factor*game.bid,partner_found)
			partner_found.remove(players[bid_winner_index])
			for i in game.partners:
				if i.player not in partner_found:
					if i.player != '':
						partner_found.add(i.player)
			add_fixed_scores_from_current_game(factor*game.bid/2,partner_found)

			if (game_winner == "np"):
				add_fixed_scores_from_current_game(game.bid, players)

		except Exception as error:
			print("Scores already added:", error)


		del players[:]
		del cards[:]
		del hands[:]
		del bidders[:]
		del rounds[:]
		player_points = {}
		game = Game(bidder="", partners=[], bid=-1, trump="")
		game_started = False
		bidding_completed = False
		partner_chosen = False
		del player_order[:]
		bid_winner = ""
		del past_rounds[:]
		player_shift = 0
		bid_winner_index = 0
		scorecard_lock.release()
		return redirect(url_for('app_game.list_players'))
	except Exception as error:
		scorecard_lock.release()
		return render_template('end_game_popup.html')

@app_game.route('/display_results')
@login_required
def display_results():
	global players, rounds, game, bid_winner_index
	player_points = {i:0 for i in players}
	for round in rounds:
		player_points[round.winner] += round.points

	team_bidder = 0

	partner_found = set()
	team_bidder += player_points[players[bid_winner_index]]
	partner_found.add(players[bid_winner_index])

	for i in game.partners:
		if i.player not in partner_found:
			team_bidder += player_points[i.player]
			partner_found.add(i.player)


	message = "Partners got " + str(team_bidder) + " points!"

	if team_bidder > game.bid:
		winner_message = "Partners Won!"
	else:
		winner_message = "Non-partners Won!"

	return render_template("display_results.html", message=message, winner_message=winner_message, player_points=player_points)