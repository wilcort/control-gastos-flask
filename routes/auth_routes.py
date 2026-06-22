import re
import secrets
from flask import url_for
from flask_mail import Message
from services.mail_service import mail
from flask import current_app

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
from services.brevo_service import send_password_reset_email


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


#! Rules for password
def validate_password(password):
    """
    Valida que la contraseña cumpla:
    - 8 caracteres mínimo
    - 1 mayúscula
    - 1 minúscula
    - 1 número
    - 1 símbolo
    """

    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."

    if not re.search(r"[A-Z]", password):
        return "Debe contener al menos una letra mayúscula."

    if not re.search(r"[a-z]", password):
        return "Debe contener al menos una letra minúscula."

    if not re.search(r"\d", password):
        return "Debe contener al menos un número."

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Debe contener al menos un carácter especial."

    return None


#! Register info
@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

        if not re.match(email_pattern, email):
            flash("Ingrese un correo electrónico válido.", "danger")
            return redirect("/register")

        if password != confirm_password:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect("/register")

        password_error = validate_password(password)

        if password_error:
            flash(password_error, "danger")
            return redirect("/register")

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash("Este correo ya está registrado.", "danger")
            return redirect("/register")

        hashed_password = generate_password_hash(
            password
        )

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

#! Forgot password
from services.brevo_service import send_password_reset_email

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email").strip().lower()

        user = User.query.filter_by(
            email=email
        ).first()

        if user:
            token = secrets.token_urlsafe(32)

            user.verification_token = token
            db.session.commit()

            reset_link = url_for(
                "auth.reset_password",
                token=token,
                _external=True
            )

            try:
                send_password_reset_email(
                    to_email=user.email,
                    user_name=user.name,
                    reset_link=reset_link
                )

            except Exception as error:
                print("ERROR AL ENVIAR CORREO BREVO:", error)

                flash(
                    "No se pudo enviar el correo en este momento. Intenta nuevamente.",
                    "danger"
                )

                return redirect("/forgot-password")

        flash(
            "Si el correo existe, enviaremos un enlace para recuperar la contraseña.",
            "info"
        )

        return redirect("/login")

    return render_template("forgot_password.html")

#! Reset password
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    user = User.query.filter_by(
        verification_token=token
    ).first()

    if not user:
        flash("Token inválido o expirado.", "danger")
        return redirect("/login")

    if request.method == "POST":

        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect(f"/reset-password/{token}")

        password_error = validate_password(password)

        if password_error:
            flash(password_error, "danger")
            return redirect(f"/reset-password/{token}")

        user.password = generate_password_hash(password)
        user.verification_token = None

        db.session.commit()

        flash("Contraseña actualizada correctamente.", "success")
        return redirect("/login")

    return render_template("reset_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()

    flash("Sesión cerrada correctamente.", "success")

    return redirect("/login")