"""
Servicio para calcular las fechas de movimientos recurrentes.

Este archivo NO crea ingresos ni gastos en la base de datos.

Su responsabilidad es únicamente calcular en qué fechas
corresponde una regla recurrente dentro de un período.
"""

import calendar

from datetime import date, timedelta


# ============================================================
# OBTENER UN DÍA VÁLIDO DEL MES
# ============================================================

def get_valid_month_day(year, month, requested_day):
    """
    Devuelve un día válido para un mes específico.

    Ejemplos:

    requested_day = 30
    febrero 2027 tiene 28 días

    Resultado:
        28

    requested_day = 31
    abril tiene 30 días

    Resultado:
        30
    """

    # monthrange devuelve:
    #
    # (día_semana_del_primer_día, cantidad_de_días_del_mes)
    #
    # Nosotros solamente necesitamos la cantidad de días.
    _, last_day = calendar.monthrange(
        year,
        month
    )

    # Si el día solicitado existe, lo usamos.
    # Si no existe, usamos el último día del mes.
    return min(
        requested_day,
        last_day
    )


# ============================================================
# CALCULAR MOVIMIENTO DIARIO
# ============================================================

def calculate_daily_dates(
    effective_start,
    end_date
):
    """
    Genera todas las fechas desde effective_start
    hasta end_date.
    """

    dates = []

    current_date = effective_start

    while current_date <= end_date:

        dates.append(current_date)

        current_date += timedelta(days=1)

    return dates


# ============================================================
# CALCULAR MOVIMIENTO SEMANAL
# ============================================================

def calculate_weekly_dates(
    effective_start,
    end_date,
    weekday
):
    """
    Calcula las fechas de una recurrencia semanal.

    Convención utilizada:

    0 = lunes
    1 = martes
    2 = miércoles
    3 = jueves
    4 = viernes
    5 = sábado
    6 = domingo
    """

    dates = []

    # weekday() utiliza exactamente la misma convención:
    #
    # lunes = 0
    # ...
    # domingo = 6

    current_weekday = effective_start.weekday()

    # Calculamos cuántos días faltan para llegar
    # al día semanal seleccionado.
    days_until_target = (
        weekday - current_weekday
    ) % 7

    current_date = (
        effective_start
        + timedelta(days=days_until_target)
    )

    # Después avanzamos semana por semana.
    while current_date <= end_date:

        dates.append(current_date)

        current_date += timedelta(days=7)

    return dates


# ============================================================
# CALCULAR MOVIMIENTO MENSUAL
# ============================================================

def calculate_monthly_dates(
    effective_start,
    end_date,
    requested_day
):
    """
    Calcula una fecha mensual.

    Si el día solicitado no existe en determinado mes,
    utiliza el último día disponible.

    Ejemplo:

    Día configurado:
        30

    Febrero 2027:
        28
    """

    dates = []

    year = effective_start.year
    month = effective_start.month

    while True:

        # Convertimos el día solicitado en un día
        # válido para el mes actual.
        valid_day = get_valid_month_day(
            year,
            month,
            requested_day
        )

        recurring_date = date(
            year,
            month,
            valid_day
        )

        # Solamente agregamos fechas que estén
        # dentro del período solicitado.
        if (
            recurring_date >= effective_start
            and recurring_date <= end_date
        ):
            dates.append(recurring_date)

        # Si ya estamos después del período,
        # terminamos el ciclo.
        if recurring_date > end_date:
            break

        # ----------------------------------------------------
        # AVANZAR AL SIGUIENTE MES
        # ----------------------------------------------------

        if month == 12:

            month = 1
            year += 1

        else:

            month += 1

    return dates


# ============================================================
# CALCULAR MOVIMIENTO QUINCENAL
# ============================================================

def calculate_biweekly_dates(
    effective_start,
    end_date,
    day_1,
    day_2
):
    """
    Calcula dos fechas por mes.

    Ejemplo:

    day_1 = 15
    day_2 = 30

    Enero:
        15
        30

    Febrero:
        15
        28
    """

    dates = []

    year = effective_start.year
    month = effective_start.month

    while True:

        # Obtener días válidos para el mes actual.
        valid_day_1 = get_valid_month_day(
            year,
            month,
            day_1
        )

        valid_day_2 = get_valid_month_day(
            year,
            month,
            day_2
        )

        first_date = date(
            year,
            month,
            valid_day_1
        )

        second_date = date(
            year,
            month,
            valid_day_2
        )

        # ----------------------------------------------------
        # AGREGAR PRIMERA FECHA
        # ----------------------------------------------------

        if (
            first_date >= effective_start
            and first_date <= end_date
        ):
            dates.append(first_date)

        # ----------------------------------------------------
        # AGREGAR SEGUNDA FECHA
        # ----------------------------------------------------

        if (
            second_date >= effective_start
            and second_date <= end_date
        ):
            dates.append(second_date)

        # Si ambas fechas terminan siendo iguales,
        # eliminaremos el duplicado más adelante.
        #
        # Ejemplo:
        # días configurados 30 y 31 en febrero
        # ambos podrían convertirse en 28.

        # Si ya estamos fuera del período,
        # podemos terminar.
        if (
            first_date > end_date
            and second_date > end_date
        ):
            break

        # ----------------------------------------------------
        # AVANZAR AL SIGUIENTE MES
        # ----------------------------------------------------

        if month == 12:

            month = 1
            year += 1

        else:

            month += 1

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS Y ORDENAR
    # --------------------------------------------------------

    dates = sorted(
        set(dates)
    )

    return dates


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def get_recurring_dates(
    recurring_item,
    start_date,
    end_date
):
    """
    Calcula las fechas de una regla recurrente
    dentro de un período.

    Parámetros:

        recurring_item:
            objeto RecurringTransaction

        start_date:
            inicio del período consultado

        end_date:
            final del período consultado

    Retorna:

        lista de objetos date


    Ejemplo:

        [
            date(2027, 2, 15),
            date(2027, 2, 28)
        ]
    """

    # --------------------------------------------------------
    # VALIDAR PERÍODO
    # --------------------------------------------------------

    if start_date > end_date:
        return []

    # --------------------------------------------------------
    # IGNORAR MOVIMIENTOS INACTIVOS
    # --------------------------------------------------------

    if not recurring_item.active:
        return []

    # --------------------------------------------------------
    # RESPETAR FECHA DE INICIO DE LA REGLA
    # --------------------------------------------------------

    # Nunca debemos generar una ocurrencia anterior
    # a start_date del movimiento recurrente.

    effective_start = max(
        start_date,
        recurring_item.start_date
    )

    # Si la regla comienza después del período consultado,
    # entonces no existe ninguna ocurrencia.
    if effective_start > end_date:
        return []

    # --------------------------------------------------------
    # DIARIO
    # --------------------------------------------------------

    if recurring_item.frequency == "daily":

        return calculate_daily_dates(
            effective_start,
            end_date
        )

    # --------------------------------------------------------
    # SEMANAL
    # --------------------------------------------------------

    if recurring_item.frequency == "weekly":

        return calculate_weekly_dates(
            effective_start,
            end_date,
            recurring_item.day_1
        )

    # --------------------------------------------------------
    # QUINCENAL
    # --------------------------------------------------------

    if recurring_item.frequency == "biweekly":

        return calculate_biweekly_dates(
            effective_start,
            end_date,
            recurring_item.day_1,
            recurring_item.day_2
        )

    # --------------------------------------------------------
    # MENSUAL
    # --------------------------------------------------------

    if recurring_item.frequency == "monthly":

        return calculate_monthly_dates(
            effective_start,
            end_date,
            recurring_item.day_1
        )

    # --------------------------------------------------------
    # FRECUENCIA DESCONOCIDA
    # --------------------------------------------------------

    return []