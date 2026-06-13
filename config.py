import os

# Base directory of the project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret key for sessions and forms
    SECRET_KEY = "dev-secret-key"

    # SQLite database path
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        BASE_DIR,
        "database",
        "control_gastos.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False