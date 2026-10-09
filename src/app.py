"""Flask application factory using Neon in normal operation."""

import os
from pathlib import Path
import secrets

import click
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import import_sqlite, neon_database_url
from src.models.user import db
from src.routes.note import note_bp
from src.routes.user import user_bp

ROOT_DIR = Path(__file__).resolve().parent.parent


def create_app(test_config=None):
    load_dotenv(ROOT_DIR / '.env')
    on_vercel = os.getenv('VERCEL') == '1'
    image_limit = (4 if on_vercel else 5) * 1024 * 1024
    static_dir = ROOT_DIR / 'public' if on_vercel else ROOT_DIR / 'src' / 'static'
    app = Flask(__name__, static_folder=str(static_dir))
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=image_limit + 256 * 1024,
        MAX_IMAGE_BYTES=image_limit,
    )
    if test_config and test_config.get('TESTING'):
        app.config.update(test_config)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = neon_database_url(os.getenv('DATABASE_URL'))
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True, 'pool_recycle': 300,
            'pool_size': 3, 'max_overflow': 2,
            'connect_args': {'connect_timeout': 10},
        }
    db.init_app(app)
    CORS(app)
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(note_bp, url_prefix='/api')

    @app.get('/api/config')
    def client_config():
        return jsonify(max_image_bytes=app.config['MAX_IMAGE_BYTES'])

    @app.errorhandler(413)
    def upload_too_large(error):
        limit_mb = app.config['MAX_IMAGE_BYTES'] // (1024 * 1024)
        return jsonify(error=f'Image upload is too large. Maximum image size is {limit_mb} MB.'), 413

    @app.errorhandler(SQLAlchemyError)
    def database_unavailable(error):
        db.session.rollback()
        return jsonify(error='Database unavailable. Check Neon configuration and initialize the tables.'), 503

    @app.cli.command('init-db')
    def init_db():
        """Create missing tables without deleting existing data."""
        try:
            db.create_all()
        except SQLAlchemyError:
            raise click.ClickException('Could not initialize Neon. Check DATABASE_URL and connectivity.') from None
        click.echo('Database tables initialized.')

    @app.cli.command('db-check')
    def db_check():
        """Verify the configured database is reachable."""
        try:
            db.session.execute(text('SELECT 1'))
        except SQLAlchemyError:
            raise click.ClickException('Could not connect to Neon. Check DATABASE_URL and connectivity.') from None
        click.echo('Database connection successful.')

    @app.cli.command('migrate-sqlite')
    @click.option('--source', type=click.Path(exists=True, dir_okay=False),
                  default=str(ROOT_DIR / 'database' / 'app.db'))
    def migrate_sqlite(source):
        """Copy old notes/users into an empty, initialized Neon database."""
        try:
            notes, users = import_sqlite(source)
        except ValueError as error:
            raise click.ClickException(str(error)) from None
        except Exception:
            raise click.ClickException('Migration failed and was rolled back. Check the source schema and Neon connection.') from None
        click.echo(f'Imported {notes} notes and {users} users. SQLite source was not changed.')

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path.startswith('api/'):
            return jsonify(error='API endpoint not found'), 404
        if path and (Path(app.static_folder) / path).is_file():
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app
