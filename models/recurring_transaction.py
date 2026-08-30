
from datetime import datetime

from models.user import db


class RecurringTransaction(db.Model):
    """
    Representa una regla recurrente de ingreso o gasto.

    Ejemplos:
    - Alquiler mensual
    - Salario quincenal
    - Supermercado semanal
    """

    __tablename__ = "recurring_transactions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Usuario propietario del movimiento recurrente.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Valores esperados:
    # "income" o "expense"
    transaction_type = db.Column(
        db.String(20),
        nullable=False
    )

    # Se utiliza principalmente para gastos.
    # En ingresos puede quedar vacío.
    category = db.Column(
        db.String(100),
        nullable=True
    )

    description = db.Column(
        db.String(150),
        nullable=False
    )

    # Mantenemos Float por ahora para no mezclar
    # esta funcionalidad con la futura migración a Numeric.
    amount = db.Column(
        db.Float,
        nullable=False
    )

    # Valores esperados:
    # daily, weekly, biweekly, monthly
    frequency = db.Column(
        db.String(20),
        nullable=False
    )

    # Uso de day_1:
    # weekly    -> día de semana
    # biweekly  -> primer día del mes
    # monthly   -> día del mes
    #
    # Para daily puede ser None.
    day_1 = db.Column(
        db.Integer,
        nullable=True
    )

    # Solo se utiliza principalmente para frecuencia quincenal.
    # Ejemplo: 15 y 30.
    day_2 = db.Column(
        db.Integer,
        nullable=True
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    # Permite detener un recurrente sin eliminarlo físicamente.
    active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )