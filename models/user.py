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

    # Password can be NULL for users authenticated with Google.
    # Traditional users will continue storing their hashed password here.
    password = db.Column(
        db.String(255),
        nullable=True
    )
    # Unique identifier provided by Google (OpenID Connect "sub").
    # It will be NULL for users who only use email/password.
    google_sub = db.Column(
    db.String(255),
    unique=True,
    nullable=True
)

    is_verified = db.Column(
        db.Boolean, default=False)
    
    verification_token = db.Column(
        db.String(255), nullable=True)
    

    currency = db.Column(
    db.String(10),
    nullable=False,
    default="USD"
    )

    def __repr__(self):
        return f"<User {self.email}>"