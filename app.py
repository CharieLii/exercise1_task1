"""Vercel Flask entrypoint; local development can still use src/main.py."""

from src.app import create_app

app = create_app()
