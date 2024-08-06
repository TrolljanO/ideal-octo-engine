"""
Manage script for Flask application with database migration support.
"""

from flask.cli import FlaskGroup
from app import create_app, db

# Create an application instance
app = create_app()

# Create a FlaskGroup for handling the command line interface
cli = FlaskGroup(app)

if __name__ == '__main__':
    cli()
