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

#! Forgot password
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

            message = Message(
                subject="Recuperar contraseña - Control de Gastos",
                recipients=[email]
            )

            message.body = f"""
Hola {user.name},

Recibimos una solicitud para restablecer tu contraseña.

Haz clic en el siguiente enlace:

{reset_link}

Si no solicitaste este cambio, puedes ignorar este mensaje.
"""

            try:
                mail.send(message)

            except Exception as error:
                print("ERROR AL ENVIAR CORREO:", error)

                flash(
                    "No se pudo enviar el correo en este momento. Intenta nuevamente.",
                    "danger"
                )

                return redirect("/forgot-password")

        flash(
            "Si el correo existe, enviaremos un enlace para recuperar la contraseña.",
            "info"
        )

        print("MAIL_USERNAME:", current_app.config.get("MAIL_USERNAME"))
        print("MAIL_SERVER:", current_app.config.get("MAIL_SERVER"))
        print("MAIL_PORT:", current_app.config.get("MAIL_PORT"))

        return redirect("/login")

    return render_template("forgot_password.html")

#!Reset password
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