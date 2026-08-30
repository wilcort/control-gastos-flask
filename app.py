import re
import os
from flask import (
    Flask,
    render_template,
    session,
    redirect,
    flash,
    request,
    send_file
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from config import Config
from models.user import User, db
from models.income import Income
from models.expense import Expense
from models.system_config import SystemConfig
from routes.auth_routes import auth_bp
from routes.auth_routes import validate_password
from werkzeug.utils import secure_filename
from flask import jsonify

from datetime import datetime, date, timedelta
from io import BytesIO
from flask import send_from_directory
from models.currency import Currency
from models.saving_goal import SavingGoal
from models.saving_contribution import SavingContribution

from openpyxl import Workbook
from openpyxl.styles import Font
from translations import translations
from flask import session
from utils.i18n import t


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from services.mail_service import mail

from sqlalchemy import func
from models.user import User
from models.income import Income
from models.expense import Expense
from services.recurring_service import get_recurring_dates

# Model for recurring incomes and expenses
from models.recurring_transaction import RecurringTransaction


# Create the Flask application

app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

mail.init_app(app)

# Connect SQLAlchemy with Flask
db.init_app(app)
app.register_blueprint(auth_bp)

def get_locale():
    return session.get("lang", "es")

# Google domein verification 
@app.route("/.well-known/assetlinks.json")
def assetlinks():

    return send_from_directory(
        "static/.well-known",
        "assetlinks.json",
        mimetype="application/json"
    )


# Protect if not login first
def login_required():
    if "user_id" not in session:
        flash(t("login_required"), "warning")
        return redirect("/login")
    return None

def admin_required():
    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    user_email = user.email.strip().lower()

    if user_email != admin_email:
        flash(
             t("admin_access_denied"),
                "danger"
        )
        return redirect("/dashboard")

    return None

#! Language
@app.route("/set-language/<lang>")
def set_language(lang):

    if lang not in ["es", "en"]:
        lang = "es"

    session["lang"] = lang

    return redirect(request.referrer or "/dashboard")


#! mostrará en navbar, títulos y correos.
@app.context_processor
def inject_translations():
    return dict(
        t=t,
        current_lang=get_locale()
    )

@app.context_processor
def inject_system_config():

    config = SystemConfig.query.first()

    if not config:
        config = SystemConfig()
        db.session.add(config)
        db.session.commit()

    return dict(system_config=config)

#! If loging = admin > admin zone
@app.context_processor
def inject_admin_data():
    is_admin = False

    if "user_id" in session:
        user = db.session.get(
            User,
            session["user_id"]
        )

        admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()

        if user:
            user_email = user.email.strip().lower()

            if user_email == admin_email:
                is_admin = True

    return dict(is_admin=is_admin)

@app.route("/sitemap.xml")
def sitemap():
    return send_from_directory("static", "sitemap.xml")

@app.route("/robots.txt")
def robots():
    return send_from_directory("static", "robots.txt")

#! UptimeRobot
@app.route("/health")
def health():
    return "OK", 200

# Main route
@app.route("/")
def index():
    return render_template("index.html")




# ========================================================
#! DASHBOARD
# ========================================================

@app.route("/dashboard")
def dashboard():

    # Verificar que el usuario haya iniciado sesión.
    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    # ====================================================
    # PERÍODO: MES ACTUAL
    # ====================================================

    today = date.today()

    current_month_start = date(
        today.year,
        today.month,
        1
    )

    if today.month == 12:
        next_month = date(
            today.year + 1,
            1,
            1
        )
    else:
        next_month = date(
            today.year,
            today.month + 1,
            1
        )

    current_month_end = (
        next_month - timedelta(days=1)
    )


    # ========================================================
    # MOVIMIENTOS REALES DEL MES ACTUAL
    # ========================================================

    incomes = Income.query.filter(
        Income.user_id == user_id,
        Income.date >= current_month_start,
        Income.date <= current_month_end
    ).all()


    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= current_month_start,
        Expense.date <= current_month_end
    ).all()


    # Totales reales registrados.
    total_incomes = sum(
        income.amount
        for income in incomes
    )

    total_expenses = sum(
        expense.amount
        for expense in expenses
    )

    balance = (
        total_incomes
        - total_expenses
    )


    # ====================================================
    # GASTOS POR CATEGORÍA
    # ====================================================

    category_totals = {}

    for expense in expenses:

        category = expense.category or "Sin categoría"

        category_totals[category] = (
            category_totals.get(category, 0)
            + expense.amount
        )


    # ====================================================
    # USUARIO
    # ====================================================

    user = db.session.get(
        User,
        user_id
    )


    # ====================================================
    # METAS DE AHORRO
    # ====================================================

    saving_goals = SavingGoal.query.filter_by(
        user_id=user_id
    ).all()

    total_saving_target = sum(
        goal.target_amount
        for goal in saving_goals
    )

    total_saved = sum(
        goal.saved_amount
        for goal in saving_goals
    )

    saving_balance = (
        total_saving_target
        - total_saved
    )

    saving_progress = 0

    if total_saving_target > 0:

        saving_progress = (
            total_saved
            / total_saving_target
        ) * 100


    # ====================================================
    # PROYECCIÓN RECURRENTE DEL MES ACTUAL
    # ====================================================

    today = date.today()

    # Primer día del mes actual.
    current_month_start = date(
        today.year,
        today.month,
        1
    )


    # Obtener primer día del siguiente mes.
    if today.month == 12:

        next_month = date(
            today.year + 1,
            1,
            1
        )

    else:

        next_month = date(
            today.year,
            today.month + 1,
            1
        )


    # Último día del mes actual.
    current_month_end = (
        next_month
        - timedelta(days=1)
    )


    # ====================================================
    # REGLAS RECURRENTES ACTIVAS
    # ====================================================

    recurring_items = (
        RecurringTransaction.query
        .filter_by(
            user_id=user_id,
            active=True
        )
        .all()
    )


    # Inicializar los totales.
    projected_recurring_income = 0
    projected_recurring_expense = 0


    # ====================================================
    # CALCULAR OCURRENCIAS DEL MES
    # ====================================================

    for item in recurring_items:

        recurring_dates = get_recurring_dates(
            item,
            current_month_start,
            current_month_end
        )


        # Número de veces que ocurre la regla
        # durante el mes.
        occurrence_count = len(
            recurring_dates
        )

        # Monto total generado por esa regla.
        projected_amount = (
            item.amount
            * occurrence_count
        )


        if item.transaction_type == "income":

            projected_recurring_income += (
                projected_amount
            )


        elif item.transaction_type == "expense":

            # Sumar al total recurrente de gastos.
            projected_recurring_expense += (
                projected_amount
            )

            # ================================================
            # SUMAR RECURRENTE A SU CATEGORÍA
            # ================================================

            category = (
                item.category
                or "Sin categoría"
            )

            category_totals[category] = (
                category_totals.get(category, 0)
                + projected_amount
            )

    # ========================================================
    # PREPARAR DATOS PARA EL GRÁFICO DE CATEGORÍAS
    # ========================================================

    category_labels = list(
        category_totals.keys()
    )

    category_values = list(
        category_totals.values()
    )
    # ====================================================
    # BALANCE RECURRENTE PROYECTADO
    # ====================================================

    projected_recurring_balance = (
        projected_recurring_income
        - projected_recurring_expense
    )

    # ========================================================
    # RESUMEN COMBINADO DEL MES
    # ========================================================

    # Ingresos totales:
    # registrados + recurrentes esperados.
    combined_monthly_income = (
        total_incomes
        + projected_recurring_income
    )


    # Gastos totales:
    # registrados + recurrentes esperados.
    combined_monthly_expense = (
        total_expenses
        + projected_recurring_expense
    )


    # Balance estimado del mes.
    combined_monthly_balance = (
        combined_monthly_income
        - combined_monthly_expense
    )


    # ====================================================
    # MOSTRAR DASHBOARD
    # ====================================================

    return render_template(
        "dashboard.html",

        user=user,

        # Movimientos reales
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance,

        # Gráficos
        category_labels=category_labels,
        category_values=category_values,

        # Ahorros
        saving_goals=saving_goals,
        total_saving_target=total_saving_target,
        total_saved=total_saved,
        saving_balance=saving_balance,
        saving_progress=saving_progress,

        # Proyección recurrente
        projected_recurring_income=projected_recurring_income,
        projected_recurring_expense=projected_recurring_expense,
        projected_recurring_balance=projected_recurring_balance,

         # Resumen combinado del mes
        combined_monthly_income=combined_monthly_income,
        combined_monthly_expense=combined_monthly_expense,
        combined_monthly_balance=combined_monthly_balance,

        # Período utilizado
        current_month_start=current_month_start,
        current_month_end=current_month_end
    )

#! Incomes enter data
@app.route("/incomes", methods=["GET", "POST"])
def incomes():
    protected = login_required()

    if protected:
        return protected
    
    user = db.session.get(
        User,
        session["user_id"]
    )

    if request.method == "POST":
        date = request.form.get("date")
        description = request.form.get("description")
        amount = request.form.get("amount")

        if not date or not description or not amount:
            flash(t("required_fields"), "danger")
            return redirect("/incomes")

        amount = float(amount)

        if amount <= 0:
            flash(t("amount_greater_than_zero"), "danger")
            return redirect("/incomes")

        new_income = Income(
            user_id=session["user_id"],
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            description=description,
            amount=amount
        )

        db.session.add(new_income)
        db.session.commit()

        flash(t("income_created_success"), "success")
        return redirect("/incomes")

    user_incomes = Income.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "incomes.html",
        user=user,
        incomes=user_incomes)

#! Expense enter data
@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    protected = login_required()

    if protected:
        return protected
    
    user = db.session.get(
        User,
        session["user_id"]
    )

    if request.method == "POST":
        date = request.form.get("date")
        category = request.form.get("category")
        description = request.form.get("description")
        amount = request.form.get("amount")

        if not date or not category or not description or not amount:
            flash(t("required_fields"), "danger")
            return redirect("/expenses")

        amount = float(amount)

        if amount <= 0:
            flash(t("amount_greater_than_zero"), "danger")
            return redirect("/expenses")

        new_expense = Expense(
            user_id=session["user_id"],
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            category=category,
            description=description,
            amount=amount
        )

        db.session.add(new_expense)
        db.session.commit()

        flash(t("expense_created_success"), "success")
        return redirect("/expenses")
   
    user_expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "expenses.html",
        user=user,
        expenses=user_expenses
    )



#! Delete expenses
@app.route("/expenses/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    protected = login_required()

    if protected:
        return protected

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]
    ).first()

    if not expense:
        flash(t("expense_not_found"), "danger")
        return redirect("/expenses")

    db.session.delete(expense)
    db.session.commit()

    flash(t("expense_deleted_success"), "success")
    return redirect("/expenses")


#! Edit expenses
@app.route("/expenses/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    protected = login_required()

    if protected:
        return protected
    
    user = db.session.get(
        User,
        session["user_id"]
    )

    expense = Expense.query.filter_by(
        id=expense_id,
        user_id=session["user_id"]
    ).first()

    if not expense:
        flash(t("expense_not_found"), "danger")
        return redirect("/expenses")

    if request.method == "POST":
        date = request.form.get("date")
        category = request.form.get("category")
        description = request.form.get("description")
        amount = request.form.get("amount")

        expense.date = datetime.strptime(date, "%Y-%m-%d").date()
        expense.category = category
        expense.description = description
        expense.amount = float(amount)

        db.session.commit()

        flash(t("expense_updated_success"), "success")
        return redirect("/expenses")

    return render_template(
        "edit_expenses.html",
        expense=expense,
        user=user
        
    )


#! Delete incomes
@app.route("/incomes/delete/<int:income_id>", methods=["POST"])
def delete_income(income_id):
    protected = login_required()

    if protected:
        return protected

    income = Income.query.filter_by(
        id=income_id,
        user_id=session["user_id"]
    ).first()

    if not income:
        flash(t("income_not_found"), "danger")
        return redirect("/incomes")

    db.session.delete(income)
    db.session.commit()

    flash(t("income_deleted_success"), "success")
    return redirect("/incomes")

#! Edit Incomes
@app.route("/incomes/edit/<int:income_id>", methods=["GET", "POST"])
def edit_income(income_id):
    protected = login_required()

    if protected:
        return protected
    
    user = db.session.get(
        User,
        session["user_id"]
    )

    income = Income.query.filter_by(
        id=income_id,
        user_id=session["user_id"]
    ).first()

    if not income:
        flash(t("income_not_found"), "danger")
        return redirect("/incomes")

    if request.method == "POST":
        date = request.form.get("date")
        description = request.form.get("description")
        amount = request.form.get("amount")

        income.date = datetime.strptime(date, "%Y-%m-%d").date()
        income.description = description
        income.amount = float(amount)

        db.session.commit()

        flash(t("income_updated_success"), "success")
        return redirect("/incomes")

    return render_template(
        "edit_income.html",
        income=income,
        user=user
    )

#! ========================================================
#! REPORTES
#! ========================================================

@app.route("/reports", methods=["GET"])
def reports():

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(
        User,
        user_id
    )


    # ====================================================
    # FECHAS DEL FILTRO
    # ====================================================

    start_date_text = request.args.get(
        "start_date",
        ""
    )

    end_date_text = request.args.get(
        "end_date",
        ""
    )


    # ====================================================
    # PERÍODO POR DEFECTO
    # ====================================================
    # Si no hay fechas seleccionadas, mostramos
    # el mes actual.

    today = date.today()

    default_start = date(
        today.year,
        today.month,
        1
    )

    if today.month == 12:

        next_month = date(
            today.year + 1,
            1,
            1
        )

    else:

        next_month = date(
            today.year,
            today.month + 1,
            1
        )

    default_end = (
        next_month - timedelta(days=1)
    )


    period_start = default_start
    period_end = default_end


    # ====================================================
    # VALIDAR FECHA INICIAL
    # ====================================================

    if start_date_text:

        try:

            period_start = datetime.strptime(
                start_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "La fecha inicial no es válida.",
                "danger"
            )

            return redirect("/reports")


    # ====================================================
    # VALIDAR FECHA FINAL
    # ====================================================

    if end_date_text:

        try:

            period_end = datetime.strptime(
                end_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "La fecha final no es válida.",
                "danger"
            )

            return redirect("/reports")


    # ====================================================
    # VALIDAR RANGO
    # ====================================================

    if period_start > period_end:

        flash(
            "La fecha inicial no puede ser mayor que la fecha final.",
            "danger"
        )

        return redirect("/reports")


    # ====================================================
    # MOVIMIENTOS REGISTRADOS
    # ====================================================

    incomes = Income.query.filter(
        Income.user_id == user_id,
        Income.date >= period_start,
        Income.date <= period_end
    ).all()


    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= period_start,
        Expense.date <= period_end
    ).all()


    # ====================================================
    # TOTALES REGISTRADOS
    # ====================================================

    registered_income_total = sum(
        income.amount
        for income in incomes
    )

    registered_expense_total = sum(
        expense.amount
        for expense in expenses
    )


    # ====================================================
    # MOVIMIENTOS RECURRENTES
    # ====================================================

    recurring_items = RecurringTransaction.query.filter_by(
        user_id=user_id,
        active=True
    ).all()


    recurring_incomes = []
    recurring_expenses = []

    recurring_income_total = 0
    recurring_expense_total = 0


    for item in recurring_items:

        recurring_dates = get_recurring_dates(
            item,
            period_start,
            period_end
        )

        for recurring_date in recurring_dates:

            movement = {
                "date": recurring_date,
                "description": item.description,
                "amount": item.amount,
                "category": item.category,
                "source": "recurring"
            }


            if item.transaction_type == "income":

                recurring_incomes.append(
                    movement
                )

                recurring_income_total += (
                    item.amount
                )


            elif item.transaction_type == "expense":

                recurring_expenses.append(
                    movement
                )

                recurring_expense_total += (
                    item.amount
                )


    # ====================================================
    # ORDENAR RECURRENTES POR FECHA
    # ====================================================

    recurring_incomes.sort(
        key=lambda item: item["date"]
    )

    recurring_expenses.sort(
        key=lambda item: item["date"]
    )


    # ====================================================
    # TOTALES COMBINADOS
    # ====================================================

    total_incomes = (
        registered_income_total
        + recurring_income_total
    )

    total_expenses = (
        registered_expense_total
        + recurring_expense_total
    )

    balance = (
        total_incomes
        - total_expenses
    )


    # ====================================================
    # MOSTRAR REPORTE
    # ====================================================

    return render_template(
        "reports.html",

        user=user,

        # Período
        period_start=period_start,
        period_end=period_end,

        # Registrados
        incomes=incomes,
        expenses=expenses,
        registered_income_total=registered_income_total,
        registered_expense_total=registered_expense_total,

        # Recurrentes
        recurring_incomes=recurring_incomes,
        recurring_expenses=recurring_expenses,
        recurring_income_total=recurring_income_total,
        recurring_expense_total=recurring_expense_total,

        # Combinados
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance
    )

#! ========================================================
#! REPORTES - EXPORTAR EXCEL
#! ========================================================

@app.route("/reports/export/excel")
def export_excel():

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(
        User,
        user_id
    )


    # ====================================================
    # MONEDA
    # ====================================================

    currency = Currency.query.filter_by(
        code=user.currency
    ).first()

    currency_symbol = (
        currency.symbol
        if currency
        else "$"
    )


    # ====================================================
    # FECHAS DEL REPORTE
    # ====================================================

    start_date_text = request.args.get(
        "start_date"
    )

    end_date_text = request.args.get(
        "end_date"
    )


    if not start_date_text or not end_date_text:

        flash(
            "Debe seleccionar un período para exportar.",
            "danger"
        )

        return redirect("/reports")


    try:

        period_start = datetime.strptime(
            start_date_text,
            "%Y-%m-%d"
        ).date()

        period_end = datetime.strptime(
            end_date_text,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        flash(
            "Las fechas del reporte no son válidas.",
            "danger"
        )

        return redirect("/reports")


    if period_start > period_end:

        flash(
            "La fecha inicial no puede ser mayor que la fecha final.",
            "danger"
        )

        return redirect("/reports")


    # ====================================================
    # MOVIMIENTOS REGISTRADOS
    # ====================================================

    incomes = Income.query.filter(
        Income.user_id == user_id,
        Income.date >= period_start,
        Income.date <= period_end
    ).all()


    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= period_start,
        Expense.date <= period_end
    ).all()


    # ====================================================
    # MOVIMIENTOS RECURRENTES
    # ====================================================

    recurring_items = RecurringTransaction.query.filter_by(
        user_id=user_id,
        active=True
    ).all()


    recurring_incomes = []
    recurring_expenses = []


    for item in recurring_items:

        recurring_dates = get_recurring_dates(
            item,
            period_start,
            period_end
        )

        for recurring_date in recurring_dates:

            movement = {
                "date": recurring_date,
                "description": item.description,
                "amount": item.amount,
                "category": item.category
            }

            if item.transaction_type == "income":

                recurring_incomes.append(
                    movement
                )

            elif item.transaction_type == "expense":

                recurring_expenses.append(
                    movement
                )


    # ====================================================
    # CREAR EXCEL
    # ====================================================

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = t(
        "financial_report"
    )


    # ====================================================
    # ENCABEZADO
    # ====================================================

    sheet.append([
        "Origen",
        t("type"),
        t("date"),
        t("category"),
        t("description"),
        t("amount")
    ])


    for cell in sheet[1]:

        cell.font = Font(
            bold=True
        )


    # Ancho de columnas.
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 18
    sheet.column_dimensions["C"].width = 15
    sheet.column_dimensions["D"].width = 22
    sheet.column_dimensions["E"].width = 35
    sheet.column_dimensions["F"].width = 18


    # ====================================================
    # INGRESOS REGISTRADOS
    # ====================================================

    for income in incomes:

        sheet.append([
            "Registrado",
            t("income"),
            income.date.strftime(
                "%Y-%m-%d"
            ),
            "",
            income.description,
            income.amount
        ])


    # ====================================================
    # INGRESOS RECURRENTES
    # ====================================================

    for income in recurring_incomes:

        sheet.append([
            "Recurrente",
            t("income"),
            income["date"].strftime(
                "%Y-%m-%d"
            ),
            "",
            income["description"],
            income["amount"]
        ])


    # ====================================================
    # GASTOS REGISTRADOS
    # ====================================================

    for expense in expenses:

        sheet.append([
            "Registrado",
            t("expense"),
            expense.date.strftime(
                "%Y-%m-%d"
            ),
            expense.category,
            expense.description,
            expense.amount
        ])


    # ====================================================
    # GASTOS RECURRENTES
    # ====================================================

    for expense in recurring_expenses:

        sheet.append([
            "Recurrente",
            t("expense"),
            expense["date"].strftime(
                "%Y-%m-%d"
            ),
            (
                expense["category"]
                or "Sin categoría"
            ),
            expense["description"],
            expense["amount"]
        ])


    # ====================================================
    # TOTALES
    # ====================================================

    registered_income_total = sum(
        income.amount
        for income in incomes
    )

    recurring_income_total = sum(
        income["amount"]
        for income in recurring_incomes
    )

    registered_expense_total = sum(
        expense.amount
        for expense in expenses
    )

    recurring_expense_total = sum(
        expense["amount"]
        for expense in recurring_expenses
    )


    total_incomes = (
        registered_income_total
        + recurring_income_total
    )

    total_expenses = (
        registered_expense_total
        + recurring_expense_total
    )

    balance = (
        total_incomes
        - total_expenses
    )


    # Línea vacía.
    sheet.append([])


    # Período.
    sheet.append([
        "Período",
        "",
        period_start.strftime("%d/%m/%Y"),
        "",
        period_end.strftime("%d/%m/%Y"),
        ""
    ])


    sheet.append([])


    # Totales.
    sheet.append([
        "Ingresos registrados",
        "",
        "",
        "",
        "",
        registered_income_total
    ])

    sheet.append([
        "Ingresos recurrentes",
        "",
        "",
        "",
        "",
        recurring_income_total
    ])

    sheet.append([
        "Ingresos totales",
        "",
        "",
        "",
        "",
        total_incomes
    ])


    sheet.append([
        "Gastos registrados",
        "",
        "",
        "",
        "",
        registered_expense_total
    ])

    sheet.append([
        "Gastos recurrentes",
        "",
        "",
        "",
        "",
        recurring_expense_total
    ])

    sheet.append([
        "Gastos totales",
        "",
        "",
        "",
        "",
        total_expenses
    ])


    sheet.append([
        "Balance estimado",
        "",
        "",
        "",
        "",
        balance
    ])


    # ====================================================
    # FORMATO MONEDA
    # ====================================================

    for row in range(
        2,
        sheet.max_row + 1
    ):

        sheet[
            f"F{row}"
        ].number_format = (
            f'"{currency_symbol}"#,##0.00'
        )


    # ====================================================
    # GENERAR ARCHIVO
    # ====================================================

    file = BytesIO()

    workbook.save(
        file
    )

    file.seek(0)


    return send_file(
        file,
        as_attachment=True,
        download_name=(
            f"{t('financial_report')}_"
            f"{period_start.strftime('%Y%m%d')}_"
            f"{period_end.strftime('%Y%m%d')}.xlsx"
        ),
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )
    )

#! Saving money
@app.route("/savings", methods=["GET", "POST"])
def savings():
    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    if request.method == "POST":
        name = request.form.get("name")
        target_amount = float(request.form.get("target_amount"))
        saved_amount = float(request.form.get("saved_amount") or 0)
        deadline = request.form.get("deadline")

        deadline_date = None

        if deadline:
            deadline_date = datetime.strptime(
                deadline,
                "%Y-%m-%d"
            ).date()

        goal = SavingGoal(
            user_id=session["user_id"],
            name=name,
            target_amount=target_amount,
            saved_amount=saved_amount,
            deadline=deadline_date
        )

        db.session.add(goal)
        db.session.commit()

        flash(t("saving_goal_created_success"), "success")
        return redirect("/savings")

    goals = SavingGoal.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "savings.html",
        goals=goals,
        user=user
    )
#! ADD monny to saving
@app.route("/savings/add/<int:goal_id>", methods=["POST"])
def add_saving_amount(goal_id):

    protected = login_required()

    if protected:
        return protected

    goal = SavingGoal.query.filter_by(
        id=goal_id,
        user_id=session["user_id"]
    ).first()

    if not goal:
        flash(t("saving_goal_not_found"), "danger")
        return redirect("/savings")

    amount = request.form.get("amount")

    if not amount:
        flash(t("enter_amount"), "danger")
        return redirect("/savings")

    amount = float(amount)

    if amount <= 0:
        flash(t("amount_greater_than_zero"), "danger")
        return redirect("/savings")

    remaining = goal.target_amount - goal.saved_amount

    if amount > remaining:
        flash(t("saving_goal_amount_exceeded").format(
        remaining=f"{remaining:,.2f}"
         ),"warning"
        )
        return redirect("/savings")

    contribution = SavingContribution(
        goal_id=goal.id,
        amount=amount
    )

    goal.saved_amount += amount

    db.session.add(contribution)
    db.session.commit()

    if goal.saved_amount >= goal.target_amount:
        flash(t("saving_goal_completed"), "success")
    else:
        flash(t("saving_added_success"), "success")

    return redirect("/savings")

#! Edit saving
@app.route("/savings/edit/<int:goal_id>", methods=["GET", "POST"])
def edit_saving_goal(goal_id):

    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    goal = SavingGoal.query.filter_by(
        id=goal_id,
        user_id=session["user_id"]
    ).first()

    if not goal:
        flash(t("saving_goal_not_found"), "danger")
        return redirect("/savings")

    if request.method == "POST":
        name = request.form.get("name")
        target_amount = request.form.get("target_amount")
        deadline = request.form.get("deadline")

        if not name or not target_amount:
            flash(t("goal_name_target_required"), "danger")
            return redirect(f"/savings/edit/{goal_id}")

        target_amount = float(target_amount)

        if target_amount <= 0:
            flash(t("target_amount_greater_zero"), "danger")
            return redirect(f"/savings/edit/{goal_id}")

        if target_amount < goal.saved_amount:
            flash(
                t("target_amount_less_saved"),
                "warning"
            )
            return redirect(f"/savings/edit/{goal_id}")

        goal.name = name
        goal.target_amount = target_amount

        if deadline:
            goal.deadline = datetime.strptime(
                deadline,
                "%Y-%m-%d"
            ).date()
        else:
            goal.deadline = None

        db.session.commit()

        flash(t("saving_goal_updated_success"), "success")
        return redirect("/savings")

    return render_template(
        "edit_saving_goal.html",
        goal=goal,
        user=user
    )

#! Delete 
@app.route("/savings/delete/<int:goal_id>", methods=["POST"])
def delete_saving_goal(goal_id):

    protected = login_required()

    if protected:
        return protected

    goal = SavingGoal.query.filter_by(
        id=goal_id,
        user_id=session["user_id"]
    ).first()

    if not goal:
        flash(t("saving_goal_not_found"), "danger")
        return redirect("/savings")

    db.session.delete(goal)
    db.session.commit()

    flash(t("saving_goal_deleted_success"), "success")
    return redirect("/savings")


#! ========================================================
#! REPORTES - EXPORTAR PDF
#! ========================================================

@app.route("/reports/export/pdf")
def export_pdf():

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(
        User,
        user_id
    )


    # ====================================================
    # CONFIGURACIÓN DEL SISTEMA
    # ====================================================

    config = SystemConfig.query.first()

    system_name = (
        config.system_name
        if config
        else "Control de Gastos"
    )


    # ====================================================
    # MONEDA
    # ====================================================

    currency = Currency.query.filter_by(
        code=user.currency
    ).first()

    currency_symbol = (
        currency.symbol
        if currency
        else "$"
    )


    # ====================================================
    # FECHAS DEL REPORTE
    # ====================================================

    start_date_text = request.args.get(
        "start_date"
    )

    end_date_text = request.args.get(
        "end_date"
    )


    # Las fechas deben venir desde Reportes.
    if not start_date_text or not end_date_text:

        flash(
            "Debe seleccionar un período para exportar.",
            "danger"
        )

        return redirect("/reports")


    # Convertir texto a fecha.
    try:

        period_start = datetime.strptime(
            start_date_text,
            "%Y-%m-%d"
        ).date()

        period_end = datetime.strptime(
            end_date_text,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        flash(
            "Las fechas del reporte no son válidas.",
            "danger"
        )

        return redirect("/reports")


    # Validar rango.
    if period_start > period_end:

        flash(
            "La fecha inicial no puede ser mayor que la fecha final.",
            "danger"
        )

        return redirect("/reports")


    # ====================================================
    # MOVIMIENTOS REGISTRADOS
    # ====================================================

    incomes = Income.query.filter(
        Income.user_id == user_id,
        Income.date >= period_start,
        Income.date <= period_end
    ).all()


    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.date >= period_start,
        Expense.date <= period_end
    ).all()


    # ====================================================
    # MOVIMIENTOS RECURRENTES
    # ====================================================

    recurring_items = RecurringTransaction.query.filter_by(
        user_id=user_id,
        active=True
    ).all()


    recurring_incomes = []
    recurring_expenses = []


    for item in recurring_items:

        recurring_dates = get_recurring_dates(
            item,
            period_start,
            period_end
        )

        for recurring_date in recurring_dates:

            movement = {
                "date": recurring_date,
                "description": item.description,
                "amount": item.amount,
                "category": item.category
            }


            if item.transaction_type == "income":

                recurring_incomes.append(
                    movement
                )


            elif item.transaction_type == "expense":

                recurring_expenses.append(
                    movement
                )


    # ====================================================
    # ORDENAR MOVIMIENTOS RECURRENTES
    # ====================================================

    recurring_incomes.sort(
        key=lambda item: item["date"]
    )

    recurring_expenses.sort(
        key=lambda item: item["date"]
    )


    # ====================================================
    # TOTALES
    # ====================================================

    registered_income_total = sum(
        income.amount
        for income in incomes
    )

    recurring_income_total = sum(
        income["amount"]
        for income in recurring_incomes
    )

    registered_expense_total = sum(
        expense.amount
        for expense in expenses
    )

    recurring_expense_total = sum(
        expense["amount"]
        for expense in recurring_expenses
    )


    total_incomes = (
        registered_income_total
        + recurring_income_total
    )

    total_expenses = (
        registered_expense_total
        + recurring_expense_total
    )

    balance = (
        total_incomes
        - total_expenses
    )


    # ====================================================
    # CREAR ARCHIVO PDF
    # ====================================================

    file = BytesIO()

    pdf = canvas.Canvas(
        file,
        pagesize=letter
    )

    pdf.setTitle(
        t("financial_report")
    )


    # ====================================================
    # FUNCIÓN AUXILIAR:
    # ENCABEZADO PARA PÁGINAS NUEVAS
    # ====================================================

    def draw_page_header():

        pdf.setFont(
            "Helvetica-Bold",
            16
        )

        pdf.drawString(
            50,
            770,
            system_name
        )

        pdf.setFont(
            "Helvetica",
            10
        )

        pdf.drawString(
            50,
            752,
            t("personal_financial_report")
        )


    # ====================================================
    # ENCABEZADO PRINCIPAL
    # ====================================================

    draw_page_header()

    pdf.setFont(
        "Helvetica",
        10
    )

    pdf.drawString(
        50,
        725,
        f"{t('user')}: {user.name}"
    )

    pdf.drawString(
        50,
        708,
        f"{t('currency')}: {user.currency}"
    )

    pdf.drawString(
        50,
        691,
        (
            f"Período: "
            f"{period_start.strftime('%d/%m/%Y')} "
            f"al "
            f"{period_end.strftime('%d/%m/%Y')}"
        )
    )

    pdf.drawString(
        50,
        674,
        (
            f"{t('date')}: "
            f"{datetime.now().strftime('%d/%m/%Y')}"
        )
    )


    # ====================================================
    # RESUMEN FINANCIERO
    # ====================================================

    pdf.rect(
        45,
        535,
        500,
        120
    )


    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawString(
        60,
        635,
        "RESUMEN DEL PERÍODO"
    )


    pdf.setFont(
        "Helvetica",
        10
    )


    pdf.drawString(
        60,
        615,
        (
            f"Ingresos registrados: "
            f"{currency_symbol}{registered_income_total:,.2f}"
        )
    )

    pdf.drawString(
        300,
        615,
        (
            f"Ingresos recurrentes: "
            f"{currency_symbol}{recurring_income_total:,.2f}"
        )
    )


    pdf.drawString(
        60,
        595,
        (
            f"Ingresos totales: "
            f"{currency_symbol}{total_incomes:,.2f}"
        )
    )


    pdf.drawString(
        60,
        575,
        (
            f"Gastos registrados: "
            f"{currency_symbol}{registered_expense_total:,.2f}"
        )
    )

    pdf.drawString(
        300,
        575,
        (
            f"Gastos recurrentes: "
            f"{currency_symbol}{recurring_expense_total:,.2f}"
        )
    )


    pdf.drawString(
        60,
        555,
        (
            f"Gastos totales: "
            f"{currency_symbol}{total_expenses:,.2f}"
        )
    )


    pdf.setFont(
        "Helvetica-Bold",
        10
    )

    pdf.drawString(
        300,
        555,
        (
            f"Balance estimado: "
            f"{currency_symbol}{balance:,.2f}"
        )
    )


    # ====================================================
    # INGRESOS
    # ====================================================

    y = 505


    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        t("incomes")
    )

    y -= 25


    # Encabezados.
    pdf.setFont(
        "Helvetica-Bold",
        9
    )

    pdf.drawString(
        50,
        y,
        "Fecha"
    )

    pdf.drawString(
        115,
        y,
        "Origen"
    )

    pdf.drawString(
        200,
        y,
        "Descripción"
    )

    pdf.drawString(
        440,
        y,
        "Monto"
    )

    y -= 10

    pdf.line(
        50,
        y,
        550,
        y
    )

    y -= 18


    # ====================================================
    # INGRESOS REGISTRADOS
    # ====================================================

    pdf.setFont(
        "Helvetica",
        9
    )


    for income in incomes:

        # Nueva página si no queda espacio.
        if y < 70:

            pdf.showPage()

            draw_page_header()

            y = 720


        pdf.drawString(
            50,
            y,
            income.date.strftime(
                "%d/%m/%Y"
            )
        )

        pdf.drawString(
            115,
            y,
            "Registrado"
        )

        pdf.drawString(
            200,
            y,
            income.description[:35]
        )

        pdf.drawString(
            440,
            y,
            (
                f"{currency_symbol}"
                f"{income.amount:,.2f}"
            )
        )

        y -= 18


    # ====================================================
    # INGRESOS RECURRENTES
    # ====================================================

    for income in recurring_incomes:

        if y < 70:

            pdf.showPage()

            draw_page_header()

            y = 720


        pdf.drawString(
            50,
            y,
            income["date"].strftime(
                "%d/%m/%Y"
            )
        )

        pdf.drawString(
            115,
            y,
            "Recurrente"
        )

        pdf.drawString(
            200,
            y,
            income["description"][:35]
        )

        pdf.drawString(
            440,
            y,
            (
                f"{currency_symbol}"
                f"{income['amount']:,.2f}"
            )
        )

        y -= 18


    # Si no existen ingresos.
    if not incomes and not recurring_incomes:

        pdf.drawString(
            50,
            y,
            "No hay ingresos en este período."
        )

        y -= 18


    # ====================================================
    # GASTOS
    # ====================================================

    y -= 20


    # Si queda poco espacio para comenzar Gastos,
    # creamos una página nueva.
    if y < 150:

        pdf.showPage()

        draw_page_header()

        y = 720


    pdf.setFont(
        "Helvetica-Bold",
        13
    )

    pdf.drawString(
        50,
        y,
        t("expenses")
    )

    y -= 25


    pdf.setFont(
        "Helvetica-Bold",
        9
    )

    pdf.drawString(
        50,
        y,
        "Fecha"
    )

    pdf.drawString(
        110,
        y,
        "Origen"
    )

    pdf.drawString(
        185,
        y,
        "Categoría"
    )

    pdf.drawString(
        285,
        y,
        "Descripción"
    )

    pdf.drawString(
        455,
        y,
        "Monto"
    )

    y -= 10

    pdf.line(
        50,
        y,
        550,
        y
    )

    y -= 18


    # ====================================================
    # GASTOS REGISTRADOS
    # ====================================================

    pdf.setFont(
        "Helvetica",
        8
    )


    for expense in expenses:

        if y < 70:

            pdf.showPage()

            draw_page_header()

            y = 720


        pdf.drawString(
            50,
            y,
            expense.date.strftime(
                "%d/%m/%Y"
            )
        )

        pdf.drawString(
            110,
            y,
            "Registrado"
        )

        pdf.drawString(
            185,
            y,
            (expense.category or "Sin categoría")[:15]
        )

        pdf.drawString(
            285,
            y,
            expense.description[:25]
        )

        pdf.drawString(
            455,
            y,
            (
                f"{currency_symbol}"
                f"{expense.amount:,.2f}"
            )
        )

        y -= 18


    # ====================================================
    # GASTOS RECURRENTES
    # ====================================================

    for expense in recurring_expenses:

        if y < 70:

            pdf.showPage()

            draw_page_header()

            y = 720


        pdf.drawString(
            50,
            y,
            expense["date"].strftime(
                "%d/%m/%Y"
            )
        )

        pdf.drawString(
            110,
            y,
            "Recurrente"
        )

        pdf.drawString(
            185,
            y,
            (
                expense["category"]
                or "Sin categoría"
            )[:15]
        )

        pdf.drawString(
            285,
            y,
            expense["description"][:25]
        )

        pdf.drawString(
            455,
            y,
            (
                f"{currency_symbol}"
                f"{expense['amount']:,.2f}"
            )
        )

        y -= 18


    # Si no existen gastos.
    if not expenses and not recurring_expenses:

        pdf.drawString(
            50,
            y,
            "No hay gastos en este período."
        )


    # ====================================================
    # PIE DE PÁGINA
    # ====================================================

    pdf.setFont(
        "Helvetica",
        8
    )

    pdf.drawString(
        50,
        30,
        f"{t('generated_by')} {system_name}"
    )


    # ====================================================
    # FINALIZAR PDF
    # ====================================================

    pdf.save()

    file.seek(0)


    return send_file(
        file,
        as_attachment=True,
        download_name=(
            f"{t('financial_report')}_"
            f"{period_start.strftime('%Y%m%d')}_"
            f"{period_end.strftime('%Y%m%d')}.pdf"
        ),
        mimetype="application/pdf"
    )

#! Edit profile
@app.route("/profile", methods=["GET", "POST"])
def profile():
    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    currencies = Currency.query.filter_by(
        is_active=True
    ).order_by(
        Currency.name.asc()
    ).all()

    if request.method == "POST":
        name = request.form.get("name").strip()
        email = request.form.get("email").strip().lower()
        currency = request.form.get("currency")

        # aquí van tus validaciones de correo duplicado...

        user.name = name
        user.email = email
        user.currency = currency

        session["user_name"] = user.name

        db.session.commit()

        flash(t("profile_updated_success"), "success")
        return redirect("/profile")

    return render_template(
        "profile.html",
        user=user,
        currencies=currencies
    )



#! change password
@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    if request.method == "POST":

        current_password = request.form.get(
            "current_password"
        )

        new_password = request.form.get(
            "new_password"
        )

        confirm_password = request.form.get(
            "confirm_password"
        )

        # Validar contraseña actual
        if not check_password_hash(
            user.password,
            current_password
        ):

            flash(
                t("current_password_incorrect"),
                "danger"
            )

            return redirect("/change-password")

        # Validar confirmación
        if new_password != confirm_password:

            flash(
                t("passwords_do_not_match"),
                "danger"
            )

            return redirect("/change-password")

        # Validar seguridad de contraseña
        password_error = validate_password(
            new_password
        )

        if password_error:

            flash(
                password_error,
                "danger"
            )

            return redirect("/change-password")

        # Evitar reutilizar la misma contraseña
        if check_password_hash(
            user.password,
            new_password
        ):

            flash(
                t("new_password_must_different"),
                "warning"
            )

            return redirect("/change-password")

        # Guardar nueva contraseña
        user.password = generate_password_hash(
            new_password
        )

        db.session.commit()

        flash(
             t("password_updated_success"),
                "success"
        )

        return redirect("/profile")

    return render_template(
        "change_password.html"
    )

#! Delete account
#! Delete account
@app.route("/profile/delete-account", methods=["POST"])
def delete_account():

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    # 1. Eliminar aportes de ahorro
    SavingContribution.query.filter_by(
        user_id=user_id
    ).delete()

    # 2. Eliminar metas de ahorro
    SavingGoal.query.filter_by(
        user_id=user_id
    ).delete()

    # 3. Eliminar gastos
    Expense.query.filter_by(
        user_id=user_id
    ).delete()

    # 4. Eliminar ingresos
    Income.query.filter_by(
        user_id=user_id
    ).delete()

    # 5. Eliminar usuario
    user = db.session.get(
        User,
        user_id
    )

    if user:
        db.session.delete(user)

    db.session.commit()

    session.clear()

    flash(
        t("account_deleted_success"),
        "success"
    )

    return redirect("/")

#! Delete account from Google play
@app.route("/delete-account")
def delete_account_info():
    return render_template("delete_account.html")

#! Admin/configuracion
@app.route("/admin/configuracion", methods=["GET", "POST"])
def admin_configuracion():

    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    user_email = user.email.strip().lower()

    if user_email != admin_email:
        flash(
             t("section_access_denied"),
             "danger"
        )
        return redirect("/dashboard")

    config = SystemConfig.query.first()

    if not config:
        config = SystemConfig()
        db.session.add(config)
        db.session.commit()

    if request.method == "POST":
        config.system_name = request.form.get("system_name")
        config.support_email = request.form.get("support_email")
        
        logo_file = request.files.get("logo")

        if logo_file and logo_file.filename:
            filename = secure_filename(logo_file.filename)
            extension = filename.rsplit(".", 1)[-1].lower()

            allowed_extensions = ["png", "jpg", "jpeg", "webp"]

            if extension not in allowed_extensions:
                flash( t("invalid_logo_format"), "danger")
                return redirect("/admin/configuracion")

            logo_path = "static/uploads/logo.png"
            logo_file.save(logo_path)

            config.logo = "/static/uploads/logo.png"

        
        db.session.commit()

        flash( t("configuration_updated_success"), "success")
        return redirect("/admin/configuracion")

    return render_template(
        "admin_configuracion.html",
        config=config
    )

#! Delete account from admin
@app.route("/admin/usuarios/eliminar/<int:user_id>", methods=["POST"])
def admin_eliminar_usuario(user_id):

    protected = admin_required()
    if protected:
        return protected

    user = db.session.get(User, user_id)

    if not user:
        flash(t("user_not_found"),"danger")
        return redirect("/admin")

    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()

    if user.email.strip().lower() == admin_email:
        flash(t("cannot_delete_admin"), "danger")
        return redirect("/admin")

    if user.id == session.get("user_id"):
        flash( t("cannot_delete_yourself"), "danger")
        return redirect("/admin")

    try:
        user_goals = SavingGoal.query.filter_by(user_id=user.id).all()

        for goal in user_goals:
            SavingContribution.query.filter_by(goal_id=goal.id).delete()

        SavingGoal.query.filter_by(user_id=user.id).delete()
        Expense.query.filter_by(user_id=user.id).delete()
        Income.query.filter_by(user_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()

        flash( t("user_deleted_success"), "success")

    except Exception as error:
        db.session.rollback()
        flash(f"Error: {error}", "danger")

    return redirect("/admin")

#! Admin zone
@app.route("/admin")
def admin_dashboard():

    protected = admin_required()

    if protected:
        return protected

    total_users = User.query.count()

    users = User.query.all()

    return render_template(
        "admin.html",
        total_users=total_users,
        users=users
    )


#! PRIVACY
@app.route("/privacy")
def privacy():
    return render_template(
        "privacy.html"
    )

@app.route("/terms")
def terms():
    return render_template(
        "terms.html"
    )



#! Filter currency
@app.template_filter("currency_symbol")
def currency_symbol(currency_code):

    currency = Currency.query.filter_by(
        code=currency_code
    ).first()

    if currency:
        return currency.symbol

    return "$"


#!adimn configuration currency
@app.route("/admin/monedas", methods=["GET", "POST"])
def admin_monedas():

    protected = admin_required()

    if protected:
        return protected

    currencies = Currency.query.order_by(
        Currency.name.asc()
    ).all()

    return render_template(
        "admin_monedas.html",
        currencies=currencies
    )


#! boton on/off currency
@app.route("/admin/monedas/toggle/<int:currency_id>", methods=["POST"])
def toggle_currency(currency_id):

    protected = admin_required()

    if protected:
        return protected

    currency = db.session.get(
        Currency,
        currency_id
    )

    if not currency:
        flash(t("currency_not_found"),"danger")
        return redirect("/admin/monedas")

    currency.is_active = not currency.is_active

    db.session.commit()

    flash( t("currency_status_updated"),
    "success")
    return redirect("/admin/monedas")

#! validate recurring days

def validate_recurring_days(frequency, day_1, day_2):
    """
    Valida y normaliza los días de una recurrencia.

    Retorna:
        (day_1, day_2, error_message)

    Si todo está correcto:
        error_message será None.
    """

    # Convertir a entero solamente si hay valor.
    try:
        day_1 = int(day_1) if day_1 not in (None, "") else None
        day_2 = int(day_2) if day_2 not in (None, "") else None

    except (TypeError, ValueError):
        return None, None, "El día seleccionado no es válido."

    # ------------------------------------------------------
    # Diario
    # No necesita días.
    # ------------------------------------------------------
    if frequency == "daily":
        return None, None, None

    # ------------------------------------------------------
    # Semanal
    # 0 = lunes ... 6 = domingo.
    # ------------------------------------------------------
    if frequency == "weekly":

        if day_1 is None or day_1 < 0 or day_1 > 6:
            return None, None, (
                "Debe seleccionar un día válido de la semana."
            )

        return day_1, None, None

    # ------------------------------------------------------
    # Quincenal
    # Necesita dos días distintos entre 1 y 31.
    # ------------------------------------------------------
    if frequency == "biweekly":

        if (
            day_1 is None
            or day_2 is None
            or day_1 < 1
            or day_1 > 31
            or day_2 < 1
            or day_2 > 31
        ):
            return None, None, (
                "Debe seleccionar dos días válidos "
                "para la frecuencia quincenal."
            )

        if day_1 == day_2:
            return None, None, (
                "Los dos días quincenales deben ser diferentes."
            )

        return day_1, day_2, None

    # ------------------------------------------------------
    # Mensual
    # Necesita un día entre 1 y 31.
    # ------------------------------------------------------
    if frequency == "monthly":

        if day_1 is None or day_1 < 1 or day_1 > 31:
            return None, None, (
                "Debe seleccionar un día válido del mes."
            )

        return day_1, None, None

    # ------------------------------------------------------
    # Frecuencia desconocida.
    # ------------------------------------------------------
    return None, None, "Frecuencia inválida."



#! Recurring transactions
@app.route("/recurring", methods=["GET", "POST"])
def recurring_transactions():
    """
    Permite crear y listar movimientos recurrentes
    pertenecientes al usuario autenticado.
    """

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(
        User,
        user_id
    )

    # --------------------------------------------------------
    # CREAR MOVIMIENTO RECURRENTE
    # --------------------------------------------------------
    if request.method == "POST":

        transaction_type = request.form.get("transaction_type")
        category = request.form.get("category")
        description = request.form.get("description")
        amount = request.form.get("amount")
        frequency = request.form.get("frequency")
        day_1 = request.form.get("day_1")
        day_2 = request.form.get("day_2")
        start_date = request.form.get("start_date")

        # ----------------------------------------------------
        # Validación de campos obligatorios
        # ----------------------------------------------------
        if (
            not transaction_type
            or not description
            or not amount
            or not frequency
            or not start_date
        ):
            flash(
                "Todos los campos obligatorios deben completarse.",
                "danger"
            )
            return redirect("/recurring")

        # ----------------------------------------------------
        # Validar tipo
        # ----------------------------------------------------
        if transaction_type not in ["income", "expense"]:
            flash(
                "Tipo de movimiento inválido.",
                "danger"
            )
            return redirect("/recurring")

        # ----------------------------------------------------
        # Categoría obligatoria solo para gastos
        # ----------------------------------------------------
        if transaction_type == "expense" and not category:
            flash(
                "Debe seleccionar una categoría para el gasto.",
                "danger"
            )
            return redirect("/recurring")

        # Los ingresos no necesitan categoría
        if transaction_type == "income":
            category = None

        # ----------------------------------------------------
        # Validar monto
        # ----------------------------------------------------
        try:
            amount = float(amount)

        except (TypeError, ValueError):
            flash(
                "El monto ingresado no es válido.",
                "danger"
            )
            return redirect("/recurring")

        if amount <= 0:
            flash(
                "El monto debe ser mayor que cero.",
                "danger"
            )
            return redirect("/recurring")

        # ----------------------------------------------------
        # Validar frecuencia
        # ----------------------------------------------------
        valid_frequencies = [
            "daily",
            "weekly",
            "biweekly",
            "monthly"
        ]

        if frequency not in valid_frequencies:
            flash(
                "Frecuencia inválida.",
                "danger"
            )
            return redirect("/recurring")

        # ----------------------------------------------------
        # Validar días según frecuencia
        # ----------------------------------------------------
        day_1, day_2, days_error = validate_recurring_days(
            frequency,
            day_1,
            day_2
        )

        if days_error:
            flash(
                days_error,
                "danger"
            )
            return redirect("/recurring")

        # ----------------------------------------------------
        # Validar fecha inicial
        # ----------------------------------------------------
        try:
            start_date_obj = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            flash(
                "La fecha de inicio no es válida.",
                "danger"
            )
            return redirect("/recurring")

        # ----------------------------------------------------
        # Crear registro
        # ----------------------------------------------------
        new_recurring = RecurringTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            category=category,
            description=description.strip(),
            amount=amount,
            frequency=frequency,
            day_1=day_1,
            day_2=day_2,
            start_date=start_date_obj,
            active=True
        )

        db.session.add(new_recurring)
        db.session.commit()

        flash(
            "Movimiento recurrente creado correctamente.",
            "success"
        )

        return redirect("/recurring")

    # --------------------------------------------------------
    # LISTAR MOVIMIENTOS RECURRENTES
    # --------------------------------------------------------
    recurring_items = RecurringTransaction.query.filter_by(
        user_id=user_id
    ).order_by(
        RecurringTransaction.created_at.desc()
    ).all()

    return render_template(
        "recurring_transactions.html",
        user=user,
        recurring_items=recurring_items
    )
#! Edit recurring transaction
@app.route(
    "/recurring/edit/<int:recurring_id>",
    methods=["GET", "POST"]
)
def edit_recurring_transaction(recurring_id):
    """
    Permite editar un movimiento recurrente
    perteneciente al usuario autenticado.
    """

    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    recurring_item = RecurringTransaction.query.filter_by(
        id=recurring_id,
        user_id=session["user_id"]
    ).first()

    # Verificamos que el movimiento exista
    # y pertenezca al usuario autenticado.
    if not recurring_item:
        flash(
            "Movimiento recurrente no encontrado.",
            "danger"
        )
        return redirect("/recurring")

    # --------------------------------------------------------
    # ACTUALIZAR MOVIMIENTO
    # --------------------------------------------------------
    if request.method == "POST":

        transaction_type = request.form.get("transaction_type")
        category = request.form.get("category")
        description = request.form.get("description")
        amount = request.form.get("amount")
        frequency = request.form.get("frequency")
        day_1 = request.form.get("day_1")
        day_2 = request.form.get("day_2")
        start_date = request.form.get("start_date")

        # ----------------------------------------------------
        # Campos obligatorios
        # ----------------------------------------------------
        if (
            not transaction_type
            or not description
            or not amount
            or not frequency
            or not start_date
        ):
            flash(
                "Todos los campos obligatorios deben completarse.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        # ----------------------------------------------------
        # Validar tipo
        # ----------------------------------------------------
        if transaction_type not in ["income", "expense"]:
            flash(
                "Tipo de movimiento inválido.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        # ----------------------------------------------------
        # Categoría obligatoria para gastos
        # ----------------------------------------------------
        if transaction_type == "expense" and not category:
            flash(
                "Debe seleccionar una categoría para el gasto.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        if transaction_type == "income":
            category = None

        # ----------------------------------------------------
        # Validar monto
        # ----------------------------------------------------
        try:
            amount = float(amount)

        except (TypeError, ValueError):
            flash(
                "El monto ingresado no es válido.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        if amount <= 0:
            flash(
                "El monto debe ser mayor que cero.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        # ----------------------------------------------------
        # Validar frecuencia
        # ----------------------------------------------------
        valid_frequencies = [
            "daily",
            "weekly",
            "biweekly",
            "monthly"
        ]

        if frequency not in valid_frequencies:
            flash(
                "Frecuencia inválida.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        # ----------------------------------------------------
        # Validar días
        # ----------------------------------------------------
        day_1, day_2, days_error = validate_recurring_days(
            frequency,
            day_1,
            day_2
        )

        if days_error:
            flash(
                days_error,
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        # ----------------------------------------------------
        # Validar fecha
        # ----------------------------------------------------
        try:
            start_date_obj = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            flash(
                "La fecha de inicio no es válida.",
                "danger"
            )
            return redirect(
                f"/recurring/edit/{recurring_id}"
            )

        # ----------------------------------------------------
        # Actualizar campos
        # ----------------------------------------------------
        recurring_item.transaction_type = transaction_type
        recurring_item.category = category
        recurring_item.description = description.strip()
        recurring_item.amount = amount
        recurring_item.frequency = frequency
        recurring_item.day_1 = day_1
        recurring_item.day_2 = day_2
        recurring_item.start_date = start_date_obj

        db.session.commit()

        flash(
            "Movimiento recurrente actualizado correctamente.",
            "success"
        )

        return redirect("/recurring")

    # --------------------------------------------------------
    # MOSTRAR FORMULARIO DE EDICIÓN
    # --------------------------------------------------------
    return render_template(
        "edit_recurring_transaction.html",
        recurring_item=recurring_item,
        user=user
    )

#! Delete recurring transaction
@app.route(
    "/recurring/delete/<int:recurring_id>",
    methods=["POST"]
)
def delete_recurring_transaction(recurring_id):
    """
    Elimina un movimiento recurrente perteneciente
    al usuario autenticado.
    """

    protected = login_required()

    if protected:
        return protected

    # Buscamos el movimiento y verificamos
    # que pertenezca al usuario autenticado.
    recurring_item = RecurringTransaction.query.filter_by(
        id=recurring_id,
        user_id=session["user_id"]
    ).first()

    if not recurring_item:
        flash(
            "Movimiento recurrente no encontrado.",
            "danger"
        )
        return redirect("/recurring")

    # Eliminamos la regla recurrente.
    db.session.delete(recurring_item)
    db.session.commit()

    flash(
        "Movimiento recurrente eliminado correctamente.",
        "success"
    )

    return redirect("/recurring")

#! boton recurring active/inactive
@app.route(
    "/recurring/toggle/<int:recurring_id>",
    methods=["POST"]
)
def toggle_recurring_transaction(recurring_id):
    """
    Activa o desactiva un movimiento recurrente
    perteneciente al usuario autenticado.
    """

    protected = login_required()

    if protected:
        return protected

    recurring_item = RecurringTransaction.query.filter_by(
        id=recurring_id,
        user_id=session["user_id"]
    ).first()

    # Evita modificar registros de otros usuarios
    if not recurring_item:
        flash(
            "Movimiento recurrente no encontrado.",
            "danger"
        )
        return redirect("/recurring")

    # Cambia True por False o False por True
    recurring_item.active = not recurring_item.active

    db.session.commit()

    if recurring_item.active:
        flash(
            "Movimiento recurrente activado correctamente.",
            "success"
        )
    else:
        flash(
            "Movimiento recurrente desactivado correctamente.",
            "success"
        )

    return redirect("/recurring")

#! recurring occurrences
# ============================================================
# OCURRENCIAS DE MOVIMIENTOS RECURRENTES
# ============================================================

@app.route("/recurring/occurrences")
def recurring_occurrences():
    """
    Calcula y prepara las ocurrencias recurrentes
    pertenecientes al usuario autenticado.

    Por defecto muestra el mes actual.

    También permite recibir:
        ?start_date=YYYY-MM-DD
        &end_date=YYYY-MM-DD
    """

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(
        User,
        user_id
    )

    # ========================================================
    # PERÍODO PREDETERMINADO
    # ========================================================

    today = date.today()

    # Primer día del mes actual.
    default_start = date(
        today.year,
        today.month,
        1
    )

    # --------------------------------------------------------
    # Calcular primer día del mes siguiente
    # para obtener después el último día del mes actual.
    # --------------------------------------------------------

    if today.month == 12:

        next_month = date(
            today.year + 1,
            1,
            1
        )

    else:

        next_month = date(
            today.year,
            today.month + 1,
            1
        )

    # Restamos un día para obtener el último día
    # del mes actual.
    from datetime import timedelta

    default_end = (
        next_month
        - timedelta(days=1)
    )

    # ========================================================
    # FECHAS RECIBIDAS DESDE LA URL
    # ========================================================

    start_date_text = request.args.get(
        "start_date"
    )

    end_date_text = request.args.get(
        "end_date"
    )

    # ========================================================
    # TIPO DE MOVIMIENTO
    # ========================================================

    transaction_type = request.args.get(
        "transaction_type",
        ""
    )

    # Valores permitidos:
    # ""        -> Todos
    # "income"  -> Ingresos
    # "expense" -> Gastos
    if transaction_type not in [
        "",
        "income",
        "expense"
    ]:
        transaction_type = ""

    # Inicialmente utilizamos el mes actual.
    period_start = default_start
    period_end = default_end

    # ========================================================
    # VALIDAR FECHA INICIAL
    # ========================================================

    if start_date_text:

        try:

            period_start = datetime.strptime(
                start_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "La fecha inicial no es válida.",
                "danger"
            )

            return redirect(
                "/recurring/occurrences"
            )

    # ========================================================
    # VALIDAR FECHA FINAL
    # ========================================================

    if end_date_text:

        try:

            period_end = datetime.strptime(
                end_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "La fecha final no es válida.",
                "danger"
            )

            return redirect(
                "/recurring/occurrences"
            )

    # ========================================================
    # VALIDAR RANGO
    # ========================================================

    if period_start > period_end:

        flash(
            "La fecha inicial no puede ser mayor "
            "que la fecha final.",
            "danger"
        )

        return redirect(
            "/recurring/occurrences"
        )

    # ========================================================
    # OBTENER REGLAS RECURRENTES
    # ========================================================

    query = RecurringTransaction.query.filter_by(
    user_id=user_id,
    active=True
    )

    # Si el usuario seleccionó un tipo específico,
    # aplicamos el filtro.
    if transaction_type:

        query = query.filter_by(
            transaction_type=transaction_type
        )

    recurring_items = query.all()

    # Aquí guardaremos las ocurrencias calculadas.
    occurrences = []

    # ========================================================
    # CALCULAR FECHAS DE CADA REGLA
    # ========================================================

    for item in recurring_items:

        recurring_dates = get_recurring_dates(
            item,
            period_start,
            period_end
        )

    

        # Cada fecha calculada se convierte
        # en una ocurrencia para mostrar en pantalla.
        for recurring_date in recurring_dates:

            occurrences.append(
                {
                    "date": recurring_date,
                    "recurring_id": item.id,
                    "transaction_type": item.transaction_type,
                    "category": item.category,
                    "description": item.description,
                    "amount": item.amount,
                    "frequency": item.frequency
                }
            )

    # ========================================================
    # ORDENAR POR FECHA
    # ========================================================

    occurrences.sort(
        key=lambda occurrence: occurrence["date"]
    )

    # ========================================================
    # CALCULAR TOTALES DEL PERÍODO
    # ========================================================

    total_recurring_income = sum(
        occurrence["amount"]
        for occurrence in occurrences
        if occurrence["transaction_type"] == "income"
    )

    total_recurring_expense = sum(
        occurrence["amount"]
        for occurrence in occurrences
        if occurrence["transaction_type"] == "expense"
    )

    recurring_balance = (
        total_recurring_income
        - total_recurring_expense
    )

    # ========================================================
    # MOSTRAR RESULTADOS
    # ========================================================

    return render_template(
    "recurring_occurrences.html",
    user=user,
    occurrences=occurrences,
    period_start=period_start,
    period_end=period_end,
    selected_transaction_type=transaction_type,
    total_recurring_income=total_recurring_income,
    total_recurring_expense=total_recurring_expense,
    recurring_balance=recurring_balance
    )

#! error
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404



with app.app_context():
    db.create_all()

    default_currencies = [
        ("USD", "Dólar estadounidense", "$"),
        ("CRC", "Colón costarricense", "₡"),
        ("EUR", "Euro", "€"),
        ("MXN", "Peso mexicano", "$"),
        ("COP", "Peso colombiano", "$"),
        ("ARS", "Peso argentino", "$"),
        ("CLP", "Peso chileno", "$"),
        ("PEN", "Sol peruano", "S/"),
        ("BRL", "Real brasileño", "R$"),
        ("CAD", "Dólar canadiense", "$")
    ]

    for code, name, symbol in default_currencies:
        exists = Currency.query.filter_by(code=code).first()

        if not exists:
            currency = Currency(
                code=code,
                name=name,
                symbol=symbol
            )

            db.session.add(currency)

    db.session.commit()

    config = SystemConfig.query.first()

    if not config:
        config = SystemConfig()
        db.session.add(config)
        db.session.commit()




#! MAIN
if __name__ == "__main__":
    app.run(debug=True)
