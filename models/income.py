from models.user import db


class Income(db.Model):
    __tablename__ = "incomes"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)