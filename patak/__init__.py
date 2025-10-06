import os
from flask import Flask
from dotenv import load_dotenv
from flask_restful import Resource, Api

def create_app(test_config = None):
	load_dotenv()
	SECRET_KEY = os.getenv('SECRET_KEY')

	# Create and configure Patak
	app = Flask(__name__, instance_relative_config = True)
	app.config.from_mapping(
		SECRET_KEY = SECRET_KEY,
		DATABASE = os.path.join(app.instance_path, 'patak.sqlite')
	)

	# If not testing load the instance config (if it exists)
	if test_config is None:
		app.config.from_pyfile('config.py', silent = True)
	else:
		# If testing, load the test config
		app.config.from_mapping(test_config)

	# Ensure the instance folder exists
	try:
		os.makedirs(app.instance_path)
	except OSError:
		pass

	api = Api(app)

	from . import db
	db.init_app(app)

	from . import auth
	app.register_blueprint(auth.bp)

	from . import main_page
	app.register_blueprint(main_page.bp)
	app.add_url_rule('/', endpoint='index')

	from . import api
	app.register_blueprint(api.bp)
	api.init_limiter(app)

	'''@app.route("/")
	def main():
		return "<h1>Welcome to Patak</h1>"'''

	return app