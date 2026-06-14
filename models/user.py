from flask_sqlalchemy import SQLAlchemy

# Create database object
db = SQLAlchemy()


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    is_verified = db.Column(
        db.Boolean, default=False)
    
    verification_token = db.Column(
        db.String(255), nullable=True)

    def __repr__(self):
        return f"<User {self.email}>"