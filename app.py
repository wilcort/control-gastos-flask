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

    saving_goals = SavingGoal.query.filter_by(
    user_id=user_id
    ).all()

    total_saving_target = sum(goal.target_amount for goal in saving_goals)
    total_saved = sum(goal.saved_amount for goal in saving_goals)
    saving_balance = total_saving_target - total_saved

    saving_progress = 0

    if total_saving_target > 0:
        saving_progress = (total_saved / total_saving_target) * 100


    return render_template(
        "dashboard.html",
        user=user,
        total_incomes=total_incomes,
        total_expenses=total_expenses,
        balance=balance,
        category_labels=category_labels,
        category_values=category_values,
        saving_goals=saving_goals,
        total_saving_target=total_saving_target,
        total_saved=total_saved,
        saving_balance=saving_balance,
        saving_progress=saving_progress
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

    user = db.session.get(User, user_id)

    currency = Currency.query.filter_by(
        code=user.currency
    ).first()

    currency_symbol = currency.symbol if currency else "$"

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = t("financial_report")

    sheet.append([
        t("type"),
        t("date"),
        t("category"),
        t("description"),
        t("amount")
    ])

    for cell in sheet[1]:
        cell.font = Font(bold=True)

    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 15
    sheet.column_dimensions["C"].width = 22
    sheet.column_dimensions["D"].width = 35
    sheet.column_dimensions["E"].width = 18

    for income in incomes:
        sheet.append([
            t("income"),
            income.date.strftime("%Y-%m-%d"),
            "",
            income.description,
            income.amount
        ])

    for expense in expenses:
        sheet.append([
            t("expense"),
            expense.date.strftime("%Y-%m-%d"),
            expense.category,
            expense.description,
            expense.amount
        ])

    total_incomes = sum(i.amount for i in incomes)
    total_expenses = sum(e.amount for e in expenses)
    balance = total_incomes - total_expenses

    sheet.append([])

    sheet.append([
        t("total_income"),
        "",
        "",
        "",
        total_incomes
    ])

    sheet.append([
        t("total_expenses"),
        "",
        "",
        "",
        total_expenses
    ])

    sheet.append([
        t("balance"),
        "",
        "",
        "",
        balance
    ])

    for row in range(2, sheet.max_row + 1):
        sheet[f"E{row}"].number_format = f'"{currency_symbol}"#,##0.00'

    file = BytesIO()
    workbook.save(file)
    file.seek(0)

    return send_file(
        file,
        as_attachment=True,
        download_name=f"{t('financial_report')}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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


# ! Reports PDF
@app.route("/reports/export/pdf")
def export_pdf():

    protected = login_required()

    if protected:
        return protected

    user_id = session["user_id"]

    user = db.session.get(User, user_id)

    config = SystemConfig.query.first()
    system_name = config.system_name if config else "Control de Gastos"

    currency = Currency.query.filter_by(code=user.currency).first()
    currency_symbol = user.currency + " "

    incomes = Income.query.filter_by(user_id=user_id).all()
    expenses = Expense.query.filter_by(user_id=user_id).all()

    total_incomes = sum(i.amount for i in incomes)
    total_expenses = sum(e.amount for e in expenses)
    balance = total_incomes - total_expenses

    file = BytesIO()

    pdf = canvas.Canvas(file, pagesize=letter)
    pdf.setTitle(t("financial_report"))

    # Encabezado
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, 770, system_name)

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, 745, t("personal_financial_report"))
    pdf.drawString(50, 725, f"{t('user')}: {user.name}")
    pdf.drawString(50, 705, f"{t('date')}: {datetime.now().strftime('%d/%m/%Y')}")
    pdf.drawString(50, 685, f"{t('currency')}: {user.currency}")

    # Resumen
    pdf.rect(45, 570, 300, 100)

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(60, 645, t("financial_summary").upper())

    pdf.setFont("Helvetica", 11)
    pdf.drawString(60, 625, f"{t('total_income')}: {currency_symbol}{total_incomes:,.2f}")
    pdf.drawString(60, 605, f"{t('total_expenses')}: {currency_symbol}{total_expenses:,.2f}")
    pdf.drawString(60, 585, f"{t('balance')}: {currency_symbol}{balance:,.2f}")

    # Ingresos
    y = 540

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, t("incomes"))
    y -= 25

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, t("date"))
    pdf.drawString(150, y, t("description"))
    pdf.drawString(400, y, t("amount"))
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
    pdf.drawString(50, y, t("expenses"))
    y -= 25

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, t("date"))
    pdf.drawString(140, y, t("category"))
    pdf.drawString(260, y, t("description"))
    pdf.drawString(430, y, t("amount"))
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
    pdf.drawString(50, 30, f"{t('generated_by')} {system_name}")

    pdf.save()

    file.seek(0)

    return send_file(
        file,
        as_attachment=True,
        download_name=f"{t('financial_report')}.pdf",
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
         t("account_deleted_success"),
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
