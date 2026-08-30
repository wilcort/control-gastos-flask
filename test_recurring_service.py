"""
Pruebas simples para recurring_service.py

Este archivo NO utiliza Flask ni la base de datos.
Solo comprueba la lógica de cálculo de fechas.
"""

from datetime import date
from types import SimpleNamespace

from services.recurring_service import get_recurring_dates


# ============================================================
# FUNCIÓN AUXILIAR PARA MOSTRAR RESULTADOS
# ============================================================

def show_dates(title, dates):
    """
    Muestra las fechas de forma fácil de leer.
    """

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    if not dates:
        print("Sin fechas")
        return

    for recurring_date in dates:
        print(
            recurring_date.strftime("%d/%m/%Y")
        )


# ============================================================
# PRUEBA 1
# MENSUAL - DÍA 30 EN FEBRERO
# ============================================================

monthly_item = SimpleNamespace(
    active=True,
    frequency="monthly",
    day_1=30,
    day_2=None,
    start_date=date(2027, 1, 1)
)

monthly_dates = get_recurring_dates(
    monthly_item,
    date(2027, 2, 1),
    date(2027, 2, 28)
)

show_dates(
    "PRUEBA 1 - Mensual día 30 en febrero",
    monthly_dates
)

assert monthly_dates == [
    date(2027, 2, 28)
]


# ============================================================
# PRUEBA 2
# SEMANAL - VIERNES
#
# Python:
# lunes = 0
# martes = 1
# miércoles = 2
# jueves = 3
# viernes = 4
# ============================================================

weekly_item = SimpleNamespace(
    active=True,
    frequency="weekly",
    day_1=4,
    day_2=None,
    start_date=date(2026, 9, 1)
)

weekly_dates = get_recurring_dates(
    weekly_item,
    date(2026, 9, 1),
    date(2026, 9, 30)
)

show_dates(
    "PRUEBA 2 - Semanal todos los viernes",
    weekly_dates
)

assert weekly_dates == [
    date(2026, 9, 4),
    date(2026, 9, 11),
    date(2026, 9, 18),
    date(2026, 9, 25)
]


# ============================================================
# PRUEBA 3
# QUINCENAL - DÍAS 15 Y 30 EN FEBRERO
# ============================================================

biweekly_item = SimpleNamespace(
    active=True,
    frequency="biweekly",
    day_1=15,
    day_2=30,
    start_date=date(2027, 1, 1)
)

biweekly_dates = get_recurring_dates(
    biweekly_item,
    date(2027, 2, 1),
    date(2027, 2, 28)
)

show_dates(
    "PRUEBA 3 - Quincenal días 15 y 30",
    biweekly_dates
)

assert biweekly_dates == [
    date(2027, 2, 15),
    date(2027, 2, 28)
]


# ============================================================
# PRUEBA 4
# DIARIO
# ============================================================

daily_item = SimpleNamespace(
    active=True,
    frequency="daily",
    day_1=None,
    day_2=None,
    start_date=date(2027, 3, 1)
)

daily_dates = get_recurring_dates(
    daily_item,
    date(2027, 3, 1),
    date(2027, 3, 5)
)

show_dates(
    "PRUEBA 4 - Diario",
    daily_dates
)

assert daily_dates == [
    date(2027, 3, 1),
    date(2027, 3, 2),
    date(2027, 3, 3),
    date(2027, 3, 4),
    date(2027, 3, 5)
]


# ============================================================
# PRUEBA 5
# RESPETAR FECHA DE INICIO
# ============================================================

start_date_item = SimpleNamespace(
    active=True,
    frequency="daily",
    day_1=None,
    day_2=None,

    # El movimiento realmente comienza el día 10.
    start_date=date(2027, 3, 10)
)

start_date_dates = get_recurring_dates(
    start_date_item,

    # Aunque consultemos desde el día 1...
    date(2027, 3, 1),

    date(2027, 3, 12)
)

show_dates(
    "PRUEBA 5 - Respetar fecha de inicio",
    start_date_dates
)

assert start_date_dates == [
    date(2027, 3, 10),
    date(2027, 3, 11),
    date(2027, 3, 12)
]


# ============================================================
# PRUEBA 6
# MOVIMIENTO INACTIVO
# ============================================================

inactive_item = SimpleNamespace(
    active=False,
    frequency="monthly",
    day_1=30,
    day_2=None,
    start_date=date(2027, 1, 1)
)

inactive_dates = get_recurring_dates(
    inactive_item,
    date(2027, 2, 1),
    date(2027, 2, 28)
)

show_dates(
    "PRUEBA 6 - Movimiento inactivo",
    inactive_dates
)

assert inactive_dates == []


# ============================================================
# RESULTADO FINAL
# ============================================================

print("\n")
print("=" * 60)
print("TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
print("=" * 60)
