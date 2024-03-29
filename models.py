from flask_login import UserMixin
from . import db

from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000), unique=True)

class Game:

	def __init__(self, bidder="", partners=[], bid=-1, trump=""):
		self.bidder = bidder
		self.partners = partners
		self.bid = bid
		self.trump = trump

class GameOfMindi:

	def __init__(self, team1=[], team2=[], trump=""):
		self.team1 = team1
		self.team2 = team2
		self.trump = trump
	
class Partner():
	
	def __init__(self, player="", suit="", value="", turn_number=-1):
		self.player = player
		self.suit = suit
		self.value = value
		self.turn_number = turn_number

class Round():

	def __init__(self, starting_player, cards=[], winner=-1, points=0):
		self.starting_player = starting_player
		self.cards = cards
		self.winner = winner
		self.points = points

class Hand():

	def __init__(self, player, cards=[]):
		self.player = player
		self.cards = cards

class Card():

	def __init__(self, suit, value, points):
		self.suit = suit
		self.value = value
		self.points = points