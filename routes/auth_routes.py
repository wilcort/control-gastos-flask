import re
import secrets

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    flash,
    session,
    url_for
)


from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.security import generate_password_hash

from models.user import User, db
from flask_mail import Message
from services.mail_service import mail




# Authentication Blueprint
auth_bp = Blueprint("auth", __name__)


# Login Page
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            flash(
                "Correo o contraseña incorrectos.",
                "danger"
            )

            return redirect("/login")
        
        if not user.is_verified:
            flash(
                  "Debes verificar tu correo electrónico antes de iniciar sesión.",
                  "warning"
               )
            return redirect("/login")

        if not check_password_hash(
            user.password,
            password
        ):

            flash(
                "Correo o contraseña incorrectos.",
                "danger"
            )

            return redirect("/login")
        
        

        # Save user session
        session["user_id"] = user.id
        session["user_name"] = user.name

        flash(
            f"Bienvenido {user.name}",
            "success"
        )

        return redirect("/dashboard")

    return render_template("login.html")


# Register User
@auth_bp.route("/register", methods=["GET", "POST"])
def register():


    # If the user submits the form
    if request.method == "POST":

        # Get form data
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validar formato del correo
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(email_pattern, email):
            flash(
                    "Ingrese un correo electrónico válido.",
                     "danger"
                    )
            return redirect("/register")

        # Validate passwords
        if password != confirm_password:
            flash(
                "Las contraseñas no coinciden.",
                "danger"
            )
            return redirect("/register")

        # Check if email already exists
        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash(
                "Este correo ya está registrado.",
                "danger"
            )
            return redirect("/register")

        # Encrypt password
        hashed_password = generate_password_hash(
            password
        )
        verification_token = secrets.token_urlsafe(32)
        # Create user object
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,

             is_verified=False,

            verification_token=verification_token
        )

        # Save to database
        db.session.add(new_user)
        db.session.commit()

      # Create verification link
        verification_link = url_for( "auth.verify_email",token=verification_token,
                    _external=True
                    )

    # Create email message
        message = Message(
                subject="Verifica tu cuenta - Control de Gastos",
                    recipients=[email]
                )

        message.body = f"""
            Hola {name},

                Gracias por registrarte en Control de Gastos.

                Para verificar tu cuenta, haz clic en el siguiente enlace:

    {verification_link}

                Si no creaste esta cuenta, puedes ignorar este mensaje.
                """

    # Send email
        mail.send(message)

        flash(
            "Usuario creado correctamente. Revisa tu correo para verificar la cuenta.",
            "success"
            )

        return redirect("/login") 

    # Show register page
    return render_template("register.html")

# Verification
@auth_bp.route("/verify/<token>")
def verify_email(token):

    user = User.query.filter_by(
        verification_token=token
    ).first()

    if not user:
        flash(
            "Token de verificación inválido.",
            "danger"
        )
        return redirect("/login")

    user.is_verified = True
    user.verification_token = None

    db.session.commit()

    flash(
        "Correo verificado correctamente. Ahora puedes iniciar sesión.",
        "success"
    )

    return redirect("/login")