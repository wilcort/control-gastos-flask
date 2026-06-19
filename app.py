import re
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
from routes.auth_routes import auth_bp

from datetime import datetime
from io import BytesIO
from flask import send_from_directory

from openpyxl import Workbook
from openpyxl.styles import Font

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from services.mail_service import mail

from sqlalchemy import func

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

    return render_template(
        "dashboard.html",
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance,category_labels=category_labels,
    category_values=category_values
    )

#! Incomes enter data
@app.route("/incomes", methods=["GET", "POST"])
def incomes():
    protected = login_required()

    if protected:
        return protected

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
        incomes=user_incomes)

#! Expense enter data
@app.route("/expenses", methods=["GET", "POST"])
def expenses():
    protected = login_required()

    if protected:
        return protected

    if request.method == "POST":
        date = request.form.get("date")
        category = request.form.get("category")
        description = request.form.get("description")
        amount = request.form.get("amount")

        if not date or not category or not description or not amount:
            flash(
                "Todos los campos son obligatorios.",
                 "danger"
                 )
            return redirect("/expenses")

        amount = float(amount)

        if amount <= 0:
            flash(
                 "El monto debe ser mayor que cero.",
                 "danger"
                )
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
#! Edit incomes
@app.route("/expenses/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
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
        expense=expense
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
        income=income
    )

#! Reports Incomes
@app.route("/reports", methods=["GET", "POST"])
def reports():
    protected = login_required()

    if protected:
        return protected

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
            income.amount
        ])

    #GASTOS
    for expense in expenses:
        sheet.append([
            "Gasto",
            expense.date.strftime("%Y-%m-%d"),
            expense.category,
            expense.description,
            expense.amount
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


#!Reports pdf
@app.route("/reports/export/pdf")
def export_pdf():
    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    total_incomes = sum(i.amount for i in incomes)
    total_expenses = sum(e.amount for e in expenses)
    balance = total_incomes - total_expenses

    file = BytesIO()

    pdf = canvas.Canvas(file, pagesize=letter)
    pdf.setTitle("Reporte Financiero")

    pdf.drawString(50, 750, "Reporte Financiero Personal")
    pdf.drawString(50, 720, f"Total Ingresos: ${total_incomes:,.2f}")
    pdf.drawString(50, 700, f"Total Gastos: ${total_expenses:,.2f}")
    pdf.drawString(50, 680, f"Balance: ${balance:,.2f}")

    y = 640

    pdf.drawString(50, y, "Ingresos")
    y -= 25

    for income in incomes:
        pdf.drawString(
            50,
            y,
            f"{income.date} - {income.description} - ${income.amount:,.2f}"
        )
        y -= 20

    y -= 20
    pdf.drawString(50, y, "Gastos")
    y -= 25

    for expense in expenses:
        pdf.drawString(
            50,
            y,
            f"{expense.date} - {expense.category} - {expense.description} - ${expense.amount:,.2f}"
        )
        y -= 20

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


#!edit profile
@app.route("/profile", methods=["GET", "POST"])
def profile():
    protected = login_required()

    if protected:
        return protected

    user = db.session.get(
        User,
        session["user_id"]
    )

    if request.method == "POST":
        name = request.form.get("name").strip()
        email = request.form.get("email").strip().lower()

        patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

        if not re.match(patron, email):
            flash("Correo electrónico inválido.", "danger")
            return redirect("/profile")

        existing_user = User.query.filter(
            func.lower(User.email) == email.lower(),
            User.id != user.id
        ).first()

        if existing_user:
            flash("Este correo ya está registrado por otro usuario.", "danger")
            return redirect("/profile")

        user.name = name
        user.email = email

        session["user_name"] = user.name

        db.session.commit()

        flash("Perfil actualizado correctamente.", "success")
        return redirect("/profile")

    return render_template("profile.html", user=user)

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

        if not check_password_hash(
            user.password,
            current_password
        ):

            flash(
                "La contraseña actual es incorrecta.",
                "danger"
            )

            return redirect("/change-password")

        if new_password != confirm_password:

            flash(
                "Las contraseñas no coinciden.",
                "danger"
            )

            return redirect("/change-password")

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


@app.route("/admin")
def admin_dashboard():

    protected = login_required()

    if protected:
        return protected
    
    user = db.session.get(
    User,
    session["user_id"]
    )

    if user.email != "wcortes779@gmail.com":
        flash(
                "No tienes permiso para acceder al panel administrador.",
                "danger"
            )
        return redirect("/dashboard")

    total_users = User.query.count()
    total_incomes = db.session.query(
        db.func.sum(Income.amount)
    ).scalar() or 0

    total_expenses = db.session.query(
        db.func.sum(Expense.amount)
    ).scalar() or 0

    balance = total_incomes - total_expenses

    users = User.query.all()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance,
        users=users
    )

#! error
@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

#! MAIN

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
