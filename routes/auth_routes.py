import re

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from models.user import User, db


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Correo o contraseña incorrectos.", "danger")
            return redirect("/login")

        if not check_password_hash(user.password, password):
            flash("Correo o contraseña incorrectos.", "danger")
            return redirect("/login")

        session["user_id"] = user.id
        session["user_name"] = user.name

        flash(f"Bienvenido {user.name}", "success")
        return redirect("/dashboard")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(email_pattern, email):
            flash("Ingrese un correo electrónico válido.", "danger")
            return redirect("/register")

        if password != confirm_password:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect("/register")

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Este correo ya está registrado.", "danger")
            return redirect("/register")

        hashed_password = generate_password_hash(password)

        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            is_verified=True,
            verification_token=None
        )

        db.session.add(new_user)
        db.session.commit()

        flash(
            "Usuario creado correctamente. Ahora puedes iniciar sesión.",
            "success"
        )

        return redirect("/login")

    return render_template("register.html")