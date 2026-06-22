from models.user import db


class Currency(db.Model):

    __tablename__ = "currencies"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    code = db.Column(
        db.String(10),
        nullable=False,
        unique=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    symbol = db.Column(
        db.String(10),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )