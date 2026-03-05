"""WSGI entrypoint (custom name requested by project)."""

from app import app

# Passenger / WSGI servers look for `application`.
application = app
