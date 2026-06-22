from models.user import db


class SystemConfig(db.Model):

    __tablename__ = "system_config"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    system_name = db.Column(
        db.String(100),
        nullable=False,
        default="Control de Gastos"
    )

    support_email = db.Column(
        db.String(150),
        nullable=False,
        default="soporte@cortessoftware.com"
    )

    logo = db.Column(
    db.String(255),
    nullable=True
    )

    currency = db.Column(
        db.String(10),
        nullable=False,
        default="USD"
    )