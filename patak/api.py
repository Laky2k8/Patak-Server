from flask import (
	Blueprint, request, session, render_template, redirect, url_for, g
)
from flask_restful import Api, Resource, reqparse, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from argon2 import PasswordHasher
from patak.db import get_db
from datetime import datetime, timedelta

import secrets
import functools

ph = PasswordHasher()

bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(bp)

auth_sessions = {}

limiter = Limiter(
	key_func=get_remote_address,
	default_limits=["200 per day", "50 per hour"],
	storage_uri="memory://"
)

def init_limiter(app):
   	# Initialize rate limiter with app
	limiter.init_app(app)

def cleanup_expired_sessions():
	# Remove expired sessions from memory
	now = datetime.now()
	expired = [
		token for token, data in auth_sessions.items()
		if 'expires_at' in data and data['expires_at'] < now
	]
	for token in expired:
		del auth_sessions[token]

def require_api_key(f):
	# Verify API key
	@functools.wraps(f)
	def decorated_function(*args, **kwargs):
		api_key = request.headers.get('X-API-Key')

		if not api_key:
			abort(401, message="An API key is required!")

		db = get_db()
		games = db.execute(
			'SELECT id, author_id, game_title, api_key FROM game'
		).fetchall()

		# Find matching game
		matching_game = None
		for game in games:
			try:
				if ph.verify(game['api_key'], api_key):
					matching_game = game
					break
			except:
				continue

		# Abort if the API key is bad
		if not matching_game:
			abort(401, message='Invalid API key')

		# Save game in memory
		g.api_game = matching_game

		return f(*args, **kwargs)
	
	return decorated_function

def require_game_session(f):
	# Validate game session token

	@functools.wraps(f)
	def decorated_function(*args, **kwargs):

		cleanup_expired_sessions()

		game_session_token = request.headers.get('X-Game-Session-Token')

		if not game_session_token or game_session_token not in auth_sessions:
			abort(412, message='Invalid or expired game session!')

		session_data = auth_sessions[game_session_token]

		if session_data.get('type') != 'game_session':
			abort(401, message='Invalid session type!')

		if session_data["game_id"] != g.api_game["id"]:
			abort(403, message='Session does not belong to this game!')

		g.game_session = session_data

		return f(*args, **kwargs)

	return decorated_function

# Authentication
class AuthInit(Resource):
	# Initialize authentication flow
	method_decorators = [require_api_key]
	decorators = [limiter.limit("10 per minute")]

	def post(self):

		cleanup_expired_sessions()

		session_token = secrets.token_urlsafe(32)

		# Store pending session
		auth_sessions[session_token] = {
			'game_id': g.api_game['id'],
			'game_title': g.api_game['game_title'],
			'status': 'pending',
			'user_id': None
		}

		auth_url = url_for('api.auth_page', token=session_token, _external = True)

		return
		{
			'session_token': session_token,
			'auth_url': auth_url,
			'expires_in': 300
		}, 200

class AuthStatus(Resource):
	# Check authentication status
	method_decorators = [require_api_key]
	decorators = [limiter.limit("60 per minute")]

	def get(self, token):

		cleanup_expired_sessions()

		if token not in auth_sessions:
			abort(404, message='Invalid token!')

		session_data = auth_sessions[token]

		if session_data['game_id'] != g.api_game['id']:
			abort(403, message='Token does not belong to this game!')

		if session_data['status'] == 'authenticated':
			# Generate a game session token 
			game_session_token = secrets.token_urlsafe(32)

			auth_sessions[game_session_token] = {
				'type': 'game_session',
				'game_id': g.api_game['id'],
				'user_id': session_data['user_id'],
				'username': session_data['username']
			}
			
			# Clean up auth session
			del auth_sessions[token]
			
			return {
				'status': 'authenticated',
				'game_session_token': game_session_token,
				'user': {
					'id': session_data['user_id'],
					'username': session_data['username']
				}
			}, 200
		
		return {'status': 'pending'}, 200

class UserInfo(Resource):
	# Get user information
	method_decorators = [require_game_session, require_api_key]
	decorators = [limiter.limit("100 per minute")]
	
	def get(self):
		db = get_db()
		user = db.execute(
			'SELECT username, coins, xp, lvl FROM user WHERE id = ?',
			(g.game_session['user_id'],)
		).fetchone()
		
		return {
			'username': user['username'],
			'coins': user['coins'],
			'xp': user['xp'],
			'level': user['lvl']
		}, 200

class UserCoins(Resource):
	#Modify user coins
	method_decorators = [require_game_session, require_api_key]
	decorators = [limiter.limit("30 per minute")]
	
	def __init__(self):
		self.parser = reqparse.RequestParser()
		self.parser.add_argument('amount', type=int, required=True, help='Amount of coins to add/subtract')
		super(UserCoins, self).__init__()
	
	def post(self):
		args = self.parser.parse_args()
		amount = args['amount']

		if abs(amount) > 100:
			abort(400, message="You're adding or subtracting too many coins!")
		
		db = get_db()
		
		# Get current coins
		user = db.execute(
			'SELECT coins FROM user WHERE id = ?',
			(g.game_session['user_id'],)
		).fetchone()
		
		new_coins = user['coins'] + amount
		
		# Prevent negative coins
		if new_coins < 0:
			abort(400, message='Insufficient coins')
		
		db.execute(
			'UPDATE user SET coins = ? WHERE id = ?',
			(new_coins, g.game_session['user_id'])
		)
		db.commit()
		
		return {
			'success': True,
			'new_balance': new_coins,
			'change': amount
		}, 200

class UserXP(Resource):
	# Modify user XP
	method_decorators = [require_game_session, require_api_key]
	decorators = [limiter.limit("30 per minute")]
	
	def __init__(self):
		self.parser = reqparse.RequestParser()
		self.parser.add_argument('amount', type=int, required=True, help='Amount of XP to add/subtract')
		super(UserXP, self).__init__()
	
	def post(self):
		args = self.parser.parse_args()
		amount = args['amount']

		if amount < 0:
			abort(400, message="You can't subtract XP!")
		
		if abs(amount) > 100:
			abort(400, message="You're adding too much XP!")
		
		db = get_db()
		
		user = db.execute(
			'SELECT xp, lvl FROM user WHERE id = ?',
			(g.game_session['user_id'],)
		).fetchone()
		
		new_xp = max(0, user['xp'] + amount)  # XP can't go below 0
		new_lvl = user['lvl']
		
		# Simple leveling: every 100 XP = 1 level
		new_lvl = 1 + (new_xp // 100)
		
		leveled_up = new_lvl > user['lvl']
		
		db.execute(
			'UPDATE user SET xp = ?, lvl = ? WHERE id = ?',
			(new_xp, new_lvl, g.game_session['user_id'])
		)
		db.commit()
		
		return {
			'success': True,
			'new_xp': new_xp,
			'new_level': new_lvl,
			'leveled_up': leveled_up,
			'change': amount
		}, 200

api.add_resource(AuthInit, '/auth/init')
api.add_resource(AuthStatus, '/auth/status/<string:token>')
api.add_resource(UserInfo, '/user/info')
api.add_resource(UserCoins, '/user/coins')
api.add_resource(UserXP, '/user/xp')

# Authentication pages
@bp.route('/auth/page')
@limiter.limit("20 per minute")
def auth_page():
	# Login page
	token = request.args.get('token')

	cleanup_expired_sessions()

	if not token or token not in auth_sessions:
		return "Invalid or expired authentication session", 400

	game_info = auth_sessions[token]

	return render_template('api/auth_page.html', token=token, game_title=game_info['game_title'])

@bp.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def auth_login():

	token = request.args.get('token')
	username = request.args.get('username')
	password = request.args.get('password')

	if not token or token not in auth_sessions:
		return "Invalid game session!", 400

	db = get_db()
	user = db.execute(
		'SELECT * FROM user WHERE username = ?', (username,)
	).fetchone()

	error = None

	if user is None:
		error = "Incorrect username!"
	else:
		if not ph.verify(user['password'], password):
			error = "Incorrect password!"
	
	if error:
		return render_template('api/auth_page.html', token = token, game_title = auth_sessions[token]['game_title'], error = error)

	auth_sessions[token]['status'] = 'authenticated'
	auth_sessions[token]['user_id'] = user['id']
	auth_sessions[token]['username'] = user['username']

	return render_template('api/auth_success.html')