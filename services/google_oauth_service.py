"""
Configuración de Google OAuth para Control de Gastos.

Este módulo centraliza la conexión con Google para evitar
tener toda la configuración OAuth directamente en auth.py.
"""

from authlib.integrations.flask_client import OAuth


# Objeto OAuth que posteriormente inicializaremos con Flask.
oauth = OAuth()


def init_google_oauth(app):
    """
    Inicializa Authlib y registra Google como proveedor OAuth.

    Las credenciales se obtienen desde la configuración de Flask,
    que a su vez las lee desde las variables de entorno.
    """

    oauth.init_app(app)

    oauth.register(
        name="google",

        # Google OpenID Connect discovery document.
        server_metadata_url=(
            "https://accounts.google.com/"
            ".well-known/openid-configuration"
        ),

        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],

        # Solicitamos únicamente la información necesaria
        # para identificar al usuario.
        client_kwargs={
            "scope": "openid email profile"
        },
    )