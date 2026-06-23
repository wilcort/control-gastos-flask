import os
import requests


def send_password_reset_email(to_email, user_name, reset_link):
    api_key = os.getenv("BREVO_API_KEY")

    url = "https://api.brevo.com/v3/smtp/email"

    sender_name = os.getenv("MAIL_FROM_NAME", "Control de Gastos")

    sender_email = os.getenv("MAIL_FROM_EMAIL", "soporte@cortessoftware.com")

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email
        },
        "to": [
            {
                "email": to_email,
                "name": user_name
            }
        ],
        "subject": "Recuperar contraseña - Control de Gastos",
        "htmlContent": f"""
            <h2>Hola {user_name}</h2>

            <p>Recibimos una solicitud para restablecer tu contraseña.</p>

            <p>Copia y pega este enlace en tu navegador:</p>

            <p>
                <a href="{reset_link}">
                    {reset_link}
                </a>
            </p>

            <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
            """
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=20
    )

    print("BREVO STATUS:", response.status_code)
    print("BREVO RESPONSE:", response.text)

    response.raise_for_status()

    return response.json()