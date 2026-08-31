import re
import secrets
from flask import url_for
from flask_mail import Message
from models import user
from services.mail_service import mail
from flask import current_app


# Cliente OAuth configurado para Google.
from services.google_oauth_service import oauth

from utils.i18n import t

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
            flash(t("invalid_credentials"), "danger")
            return redirect("/login")

        # Si el usuario fue creado con Google, no tendrá contraseña local.
        # También validamos normalmente la contraseña para usuarios tradicionales.
        if not user.password or not check_password_hash(user.password, password):
            flash(t("invalid_credentials"), "danger")
            return redirect("/login")

        session["user_id"] = user.id
        session["user_name"] = user.name

        flash(f"{t('welcome_user')} {user.name}", "success")
        return redirect("/dashboard")

    return render_template("login.html")

@auth_bp.route("/auth/google")
def google_login():
    """
    Inicia el proceso de autenticación con Google.
    """

    # URL local o de producción a la que Google devolverá al usuario.
    redirect_uri = url_for(
        "auth.google_callback",
        _external=True
    )

    # Envía al usuario a la pantalla oficial de Google.
    return oauth.google.authorize_redirect(
        redirect_uri
    )


@auth_bp.route("/auth/google/callback")
def google_callback():
    """
    Recibe la respuesta de Google después del inicio de sesión.
    """

    try:
        # Intercambia el código recibido por los tokens de Google.
        token = oauth.google.authorize_access_token()

        # Authlib obtiene los datos del usuario desde OpenID Connect.
        user_info = token.get("userinfo")

        if not user_info:
            flash("No se pudo obtener la información de Google.", "danger")
            return redirect("/login")

        # Identificador único y permanente de la cuenta Google.
        google_sub = user_info.get("sub")

        # Normalizamos el correo para evitar duplicados por mayúsculas.
        email = (user_info.get("email") or "").strip().lower()

        # Nombre mostrado en la cuenta Google.
        name = (user_info.get("name") or email).strip()

        # Google indica si verificó el correo.
        email_verified = user_info.get("email_verified", False)

        if not google_sub or not email:
            flash("Google no devolvió la información necesaria.", "danger")
            return redirect("/login")

        if not email_verified:
            flash("La cuenta de Google no tiene el correo verificado.", "danger")
            return redirect("/login")

        # ----------------------------------------------------------
        # 1. Buscar primero por identificador único de Google.
        # ----------------------------------------------------------
        user = User.query.filter_by(
            google_sub=google_sub
        ).first()

        if user:
            session["user_id"] = user.id
            session["user_name"] = user.name

            return redirect("/dashboard")

        # ----------------------------------------------------------
        # 2. Si Google es nuevo, revisar si el correo ya existe.
        # ----------------------------------------------------------
        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            # Por seguridad no vinculamos automáticamente una cuenta
            # tradicional existente con Google.
            flash(
                "Ya existe una cuenta con este correo. "
                "Inicia sesión con tu contraseña.",
                "warning"
            )
            return redirect("/login")

        # ----------------------------------------------------------
        # 3. Crear automáticamente un usuario nuevo de Google.
        # ----------------------------------------------------------
        new_user = User(
            name=name,
            email=email,
            password=None,
            google_sub=google_sub,
            is_verified=True,
            verification_token=None,
            currency="USD"
        )

        db.session.add(new_user)
        db.session.commit()

        # ----------------------------------------------------------
        # 4. Crear la sesión Flask.
        # ----------------------------------------------------------
        session["user_id"] = new_user.id
        session["user_name"] = new_user.name

        return redirect("/dashboard")

    except Exception as error:
        current_app.logger.exception(
            "Error durante Google OAuth: %s",
            error
        )

        flash(
            "No fue posible iniciar sesión con Google.",
            "danger"
        )

        return redirect("/login")


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
        return t("password_min_length")

    if not re.search(r"[A-Z]", password):
        return t("password_uppercase")

    if not re.search(r"[a-z]", password):
        return t("password_lowercase")

    if not re.search(r"\d", password):
        return t("password_number")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return t("password_special")

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
            flash(t("invalid_email"), "danger")
            return redirect("/register")

        if password != confirm_password:
            flash(t("passwords_do_not_match"), "danger")
            return redirect("/register")

        password_error = validate_password(password)

        if password_error:
            flash(password_error, "danger")
            return redirect("/register")

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash(t("email_already_registered"), "danger")
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

        flash(t("user_created_success"), "success")

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
           

                flash(t("email_send_error"), "danger")

                return redirect("/forgot-password")

        flash(t("email_sent_if_exists"), "info")

        return redirect("/login")

    return render_template("forgot_password.html")

#! Reset password
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    user = User.query.filter_by(
        verification_token=token
    ).first()

    if not user:
        flash(t("invalid_or_expired_token"), "danger")
        return redirect("/login")

    if request.method == "POST":

        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash(t("passwords_do_not_match"), "danger")
            return redirect(f"/reset-password/{token}")

        password_error = validate_password(password)

        if password_error:
            flash(password_error, "danger")
            return redirect(f"/reset-password/{token}")

        user.password = generate_password_hash(password)
        user.verification_token = None

        db.session.commit()

        flash(t("password_updated_success"), "success")
        return redirect("/login")

    return render_template("reset_password.html")


@auth_bp.route("/logout")
def logout():
    session.clear()

    flash(t("logout_success"), "success")

    return redirect("/login")