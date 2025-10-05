from flask import (
	Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
from argon2 import PasswordHasher

from patak.auth import login_required
from patak.db import get_db

ph = PasswordHasher()

bp = Blueprint('main_page', __name__)

# Helpers
def get_game(id, check_author=True):
	db = get_db()

	if id is None:
		abort(404, "No ID!")

	game = db.execute(
		'SELECT g.id, creator, game_title, api_key, game_url, created, author_id'
		' FROM game g JOIN user u ON g.author_id = u.id'
		' WHERE g.id = ?',
		(id,)
	).fetchone()

	if game is None:
		abort(404, f"Game with ID {id} doesn't exist!")

	if check_author and game["author_id"] != g.user["id"] and not g.user["is_admin"]:
		abort(403)

	return game

@bp.route('/')
@login_required
def main():
	db = get_db()

	userData = db.execute('SELECT username, coins, xp, lvl FROM user WHERE id = ?', (g.user['id'],)).fetchone()

	return render_template('site/index.html', user=userData, active_page="main")

@bp.route('/mygames')
@login_required
def my_games():

	db = get_db()

	games = db.execute(
		'SELECT g.id, g.author_id, game_title, created, creator, game_url'
		' FROM game g JOIN user u ON g.author_id = u.id'
		' ORDER BY created DESC'
	).fetchall()

	return render_template('site/my_games.html', games=games, active_page="my_games")

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create_game():
	if request.method == 'POST':
		title = request.form['title']
		error = None

		if not title:
			error = 'A game title is required!'

		if error is not None:
			flash(error)
		else:
			
			# Generate API key (24 random alphanumeric characters)
			import random, string
			api_key = ''.join(random.choices(string.ascii_letters + string.digits, k=24))

			db = get_db()
			try:
				db.execute(
					'INSERT INTO game (game_title, api_key, author_id, creator) VALUES (?, ?, ?, ?)',
					(title, ph.hash(api_key), g.user['id'], g.user['username'])
				)
				db.commit()
			except:
				error = 'This game title is already in use!'
				flash(error)
			else:
				flash(f'Game created successfully! Your API key is: {api_key}.\nSave this now, you won\'t see it again!')

				return redirect(url_for('main_page.my_games'))
		
	return render_template('site/create.html', active_page="create_game")


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update_game(id):
	game = get_game(id, check_author=True)

	if request.method == "POST":
		title = request.form["title"]
		game_url = request.form["url"]
		error = None

		if not title:
			error = "Title is required"

		if game_url:
			if not (game_url.startswith("http://") or game_url.startswith("https://")):
				error = "URL must start with http:// or https://"
			elif " " in game_url:
				error = "URL cannot contain spaces"
			

		if error is not None:
			flash(error)
		else:
			db = get_db()

			try:
				db.execute(
					'UPDATE game SET game_title = ?, game_url = ?'
					'WHERE id = ?',
					(title, game_url, id)
				)
				db.commit()
			except:
				error = "This game title or URL is already in use!"
				flash(error)
			else:
				return redirect(url_for("main_page.main"))

	return render_template('site/update.html', game=game, active_page="update_game")


@bp.route('/<int:id>/details', methods=('GET', 'POST'))
@login_required
def game_details(id):
	game = get_game(id)

	return render_template('site/details.html', game=game, active_page="game_details")