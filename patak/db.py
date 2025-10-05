import sqlite3
from datetime import datetime
import dotenv
from argon2 import PasswordHasher

import click
from flask import current_app, g # current_app points to the flask application handling the request, g is used to store data that might be accessed by multiple functions during the request

def init_db():
	db = get_db()

	ph = PasswordHasher()

	adminUser = dotenv.get_key(dotenv.find_dotenv(), "ADMIN_USERNAME")
	adminPW = dotenv.get_key(dotenv.find_dotenv(), "ADMIN_PASSWORD")

	with current_app.open_resource('schema.sql') as f:
		db.executescript(f.read().decode('utf8'))

	# Create admin user
	db.execute(
		'INSERT INTO user (username, password, coins, xp, lvl, is_admin) VALUES (?, ?, 0, 0, 1, ?)',
		(adminUser, ph.hash(adminPW), True)
	)
	db.commit()

def get_db():
	if 'db' not in g:
		g.db = sqlite3.connect(
			current_app.config['DATABASE'],
			detect_types = sqlite3.PARSE_DECLTYPES
		)
		g.db.row_factory = sqlite3.Row

	return g.db

def close_db(e = None):
	db = g.pop('db', None)

	if db is not None:
		db.close()

@click.command('init-db')
def init_db_command():
	# Clear existing data and create new tables
	init_db()
	click.echo("Initialized the database.")

def init_app(app):
	app.teardown_appcontext(close_db)
	app.cli.add_command(init_db_command)

sqlite3.register_converter("timestamp", lambda v: datetime.fromisoformat(v.decode()))