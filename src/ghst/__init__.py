from importlib import metadata

from . import app

__version__ = metadata.version("ghst")
cli = app.cli
