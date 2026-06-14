import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE_DIR = os.path.join(
    BASE_DIR,
    "database"
)

os.makedirs(DATABASE_DIR, exist_ok=True)


class Config:

    SECRET_KEY = "dev-secret-key"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        DATABASE_DIR,
        "control_gastos.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False