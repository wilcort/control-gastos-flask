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

from werkzeug.security import generate_password_hash

from models.user import User, db


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

        # Create user object
        new_user = User(
            name=name,
            email=email,
            password=hashed_password
        )

        # Save to database
        db.session.add(new_user)
        db.session.commit()

        # Success message
        flash(
            "Usuario creado correctamente. Ahora puedes iniciar sesión.",
            "success"
        )

        # Redirect to login page
        return redirect("/login")

    # Show register page
    return render_template("register.html")