from flask import Blueprint, request, session, render_template, redirect, url_for, g
from flask_restful import Api, Resource, reqparse, abort
from argon2 import PasswordHasher
from patak.db import get_db
import secrets
import functools

ph = PasswordHasher()

bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(bp)

auth_sessions = {}

def require_api_key(f):
	""" Verify API key """
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

	def post(self):
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

	def get(self, token):
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
