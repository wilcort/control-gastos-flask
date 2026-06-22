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

from datetime import datetime
from io import BytesIO
from flask import send_from_directory
from models.currency import Currency

from openpyxl import Workbook
from openpyxl.styles import Font

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from services.mail_service import mail

from sqlalchemy import func

from models.user import User
from models.income import Income
from models.expense import Expense

# Create the Flask application

app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

mail.init_app(app)

# Connect SQLAlchemy with Flask
db.init_app(app)


app.register_blueprint(auth_bp)

# Protect if not login first
def login_required():
    if "user_id" not in session:
        flash("Debes iniciar sesión para acceder.", "warning")
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
            "No tienes permiso para acceder al panel administrador.",
            "danger"
        )
        return redirect("/dashboard")

    return None

#! mostrará en navbar, títulos y correos.
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



# dashboard
@app.route("/dashboard")
def dashboard():
    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    total_incomes = sum(income.amount for income in incomes)
    total_expenses = sum(expense.amount for expense in expenses)

    balance = total_incomes - total_expenses

    category_totals = {}

    for expense in expenses:
        category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount

    category_labels = list(category_totals.keys())
    category_values = list(category_totals.values())

    user = db.session.get(
    User,
    session["user_id"]
        )

    return render_template(
        "dashboard.html",
        user=user,
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance,
        category_labels=category_labels,
        category_values=category_values
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
            flash("Todos los campos son obligatorios.", "danger")
            return redirect("/incomes")

        amount = float(amount)

        if amount <= 0:
            flash("El monto debe ser mayor que cero.", "danger")
            return redirect("/incomes")

        new_income = Income(
            user_id=session["user_id"],
            date=datetime.strptime(date, "%Y-%m-%d").date(),
            description=description,
            amount=amount
        )

        db.session.add(new_income)
        db.session.commit()

        flash("Ingreso registrado correctamente.", "success")
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
            flash("Todos los campos son obligatorios.", "danger")
            return redirect("/expenses")

        amount = float(amount)

        if amount <= 0:
            flash("El monto debe ser mayor que cero.", "danger")
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

        flash("Gasto registrado correctamente.", "success")
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
        flash("Gasto no encontrado.", "danger")
        return redirect("/expenses")

    db.session.delete(expense)
    db.session.commit()

    flash("Gasto eliminado correctamente.", "success")
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
        flash("Gasto no encontrado.", "danger")
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

        flash("Gasto actualizado correctamente.", "success")
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
        flash("Ingreso no encontrado.", "danger")
        return redirect("/incomes")

    db.session.delete(income)
    db.session.commit()

    flash("Ingreso eliminado correctamente.", "success")
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
        flash("Ingreso no encontrado.", "danger")
        return redirect("/incomes")

    if request.method == "POST":
        date = request.form.get("date")
        description = request.form.get("description")
        amount = request.form.get("amount")

        income.date = datetime.strptime(date, "%Y-%m-%d").date()
        income.description = description
        income.amount = float(amount)

        db.session.commit()

        flash("Ingreso actualizado correctamente.", "success")
        return redirect("/incomes")

    return render_template(
        "edit_income.html",
        income=income,
        user=user
    )

#! Reports Incomes
@app.route("/reports", methods=["GET", "POST"])
def reports():
    protected = login_required()

    if protected:
        return protected
    
    user = db.session.get(
        User,
        session["user_id"]
    )

    user_id = session["user_id"]

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    incomes_query = Income.query.filter_by(user_id=user_id)
    expenses_query = Expense.query.filter_by(user_id=user_id)

    if start_date and end_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        incomes_query = incomes_query.filter(
            Income.date >= start_date_obj,
            Income.date <= end_date_obj
        )

        expenses_query = expenses_query.filter(
            Expense.date >= start_date_obj,
            Expense.date <= end_date_obj
        )

    incomes = incomes_query.all()
    expenses = expenses_query.all()

    total_incomes = sum(income.amount for income in incomes)
    total_expenses = sum(expense.amount for expense in expenses)
    balance = total_incomes - total_expenses

    return render_template(
        "reports.html",
        user=user,
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance,
        incomes=incomes,
        expenses=expenses
    )

# !Reports Excel
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

    currency = Currency.query.filter_by(
        code=user.currency
    ).first()

    currency_symbol = currency.symbol if currency else "$"

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte Financiero"

    sheet.append(["TIPO", "FECHA", "CATEGORÍA", "DESCRIPCIÓN", "MONTO"])
    # Encabezados en negrita
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    # Ancho de columnas
    sheet.column_dimensions["A"].width = 15
    sheet.column_dimensions["B"].width = 15
    sheet.column_dimensions["C"].width = 20
    sheet.column_dimensions["D"].width = 30
    sheet.column_dimensions["E"].width = 15

    #INGRESOS
    for income in incomes:
        sheet.append([
            "Ingreso",
            income.date.strftime("%Y-%m-%d"),
            "",
            income.description,
            f"{currency_symbol}{income.amount:,.2f}"
        ])

    #GASTOS
    for expense in expenses:
        sheet.append([
            "Gasto",
            expense.date.strftime("%Y-%m-%d"),
            expense.category,
            expense.description,
            f"{currency_symbol}{income.amount:,.2f}"
        ])

    #TOTALES
    total_incomes = sum(i.amount for i in incomes)
    total_expenses = sum(e.amount for e in expenses)
    balance = total_incomes - total_expenses

    sheet.append([])

    sheet.append([
        "TOTAL INGRESOS",
        "",
        "",
        "",
        total_incomes
    ])

    sheet.append([
        "TOTAL GASTOS",
        "",
        "",
        "",
        total_expenses
    ])

    sheet.append([
        "BALANCE",
        "",
        "",
        "",
        balance
    ])

    file = BytesIO()
    workbook.save(file)
    file.seek(0)

    return send_file(
            file,
            as_attachment=True,
            download_name="reporte_financiero.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )



#! Reports PDF
@app.route("/reports/export/pdf")
def export_pdf():
    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(User, user_id)

    config = SystemConfig.query.first()
    system_name = config.system_name if config else "Control de Gastos"

    currency_symbol = f"{user.currency} "

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    total_incomes = sum(i.amount for i in incomes)
    total_expenses = sum(e.amount for e in expenses)
    balance = total_incomes - total_expenses

    file = BytesIO()

    pdf = canvas.Canvas(file, pagesize=letter)
    pdf.setTitle("Reporte Financiero")

    # Encabezado
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 770, system_name)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 745, "Reporte Financiero Personal")
    pdf.drawString(50, 725, f"Usuario: {user.name}")
    pdf.drawString(50, 705, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
    pdf.drawString(50, 685, f"Moneda: {user.currency}")

    # Resumen
    pdf.rect(45, 570, 280, 100)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, 645, "RESUMEN FINANCIERO")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, 625, f"Total Ingresos: {currency_symbol}{total_incomes:,.2f}")
    pdf.drawString(60, 605, f"Total Gastos: {currency_symbol}{total_expenses:,.2f}")
    pdf.drawString(60, 585, f"Balance: {currency_symbol}{balance:,.2f}")

    # Ingresos
    y = 540

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Ingresos")
    y -= 25

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Fecha")
    pdf.drawString(150, y, "Descripción")
    pdf.drawString(400, y, "Monto")
    y -= 15

    pdf.line(50, y, 550, y)
    y -= 20

    pdf.setFont("Helvetica", 10)

    for income in incomes:
        pdf.drawString(50, y, income.date.strftime("%Y-%m-%d"))
        pdf.drawString(150, y, income.description[:35])
        pdf.drawString(400, y, f"{currency_symbol}{income.amount:,.2f}")
        y -= 20

        if y < 80:
            pdf.showPage()
            y = 750

    # Gastos
    y -= 20

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Gastos")
    y -= 25

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, "Fecha")
    pdf.drawString(140, y, "Categoría")
    pdf.drawString(260, y, "Descripción")
    pdf.drawString(430, y, "Monto")
    y -= 15

    pdf.line(50, y, 550, y)
    y -= 20

    pdf.setFont("Helvetica", 10)

    for expense in expenses:
        pdf.drawString(50, y, expense.date.strftime("%Y-%m-%d"))
        pdf.drawString(140, y, expense.category[:18])
        pdf.drawString(260, y, expense.description[:25])
        pdf.drawString(430, y, f"{currency_symbol}{expense.amount:,.2f}")
        y -= 20

        if y < 80:
            pdf.showPage()
            y = 750

    # Pie de página
    pdf.setFont("Helvetica", 8)
    pdf.drawString(50, 30, f"Generado por {system_name}")

    pdf.save()

    file.seek(0)

    return send_file(
        file,
        as_attachment=True,
        download_name="reporte_financiero.pdf",
        mimetype="application/pdf"
    )
# Create database tables
# with app.app_context():
#     db.create_all()


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

        flash("Perfil actualizado correctamente.", "success")
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
                "La contraseña actual es incorrecta.",
                "danger"
            )

            return redirect("/change-password")

        # Validar confirmación
        if new_password != confirm_password:

            flash(
                "Las contraseñas no coinciden.",
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
                "La nueva contraseña debe ser diferente a la actual.",
                "warning"
            )

            return redirect("/change-password")

        # Guardar nueva contraseña
        user.password = generate_password_hash(
            new_password
        )

        db.session.commit()

        flash(
            "Contraseña actualizada correctamente.",
            "success"
        )

        return redirect("/profile")

    return render_template(
        "change_password.html"
    )

#! Delete account
@app.route("/delete-account", methods=["POST"])
def delete_account():

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    Expense.query.filter_by(
        user_id=user_id
    ).delete()

    Income.query.filter_by(
        user_id=user_id
    ).delete()

    user = db.session.get(
    User,
    user_id
    )

    db.session.delete(user)
    db.session.commit()

    session.clear()

    flash(
        "Tu cuenta fue eliminada correctamente.",
        "success"
    )

    return redirect("/")

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
            "No tienes permiso para acceder a esta sección.",
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
                flash("Formato de logo no permitido. Usa PNG, JPG, JPEG o WEBP.", "danger")
                return redirect("/admin/configuracion")

            logo_path = "static/uploads/logo.png"
            logo_file.save(logo_path)

            config.logo = "/static/uploads/logo.png"

        
        db.session.commit()

        flash("Configuración actualizada correctamente.", "success")
        return redirect("/admin/configuracion")

    return render_template(
        "admin_configuracion.html",
        config=config
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
        flash("Moneda no encontrada.", "danger")
        return redirect("/admin/monedas")

    currency.is_active = not currency.is_active

    db.session.commit()

    flash("Estado de la moneda actualizado correctamente.", "success")
    return redirect("/admin/monedas")


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
