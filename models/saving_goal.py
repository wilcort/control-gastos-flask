from models.user import db


class SavingGoal(db.Model):

    __tablename__ = "saving_goals"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    target_amount = db.Column(
        db.Float,
        nullable=False
    )

    saved_amount = db.Column(
        db.Float,
        nullable=False,
        default=0
    )

    deadline = db.Column(
        db.Date,
        nullable=True
    )

    contributions = db.relationship(
    "SavingContribution",
    backref="goal",
    lazy=True,
    cascade="all, delete-orphan"
    )