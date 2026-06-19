# Control de Gastos

Sistema web para la administración de ingresos, gastos y reportes financieros personales.

## Demo

https://gastos.cortessoftware.com

---

## Características

- Registro de usuarios
- Inicio de sesión seguro
- Recuperación de contraseña
- Gestión de ingresos
- Gestión de gastos
- Dashboard financiero
- Reportes interactivos
- Exportación a Excel
- Exportación a PDF
- Perfil de usuario
- Panel de administración
- Modo oscuro
- Diseño responsive
- Base de datos PostgreSQL

---

## Tecnologías utilizadas

### Backend

- Python 3
- Flask
- SQLAlchemy
- Flask-Migrate
- PostgreSQL

### Frontend

- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Chart.js

### Infraestructura

- Render
- PostgreSQL Render
- GitHub

---

## Capturas

### Dashboard

Agregar captura aquí

### Reportes

Agregar captura aquí

### Gestión de gastos

Agregar captura aquí

---

## Instalación Local

Clonar repositorio:

```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
```

Entrar al proyecto:

```bash
cd control_gastos
```

Crear entorno virtual:

```bash
python -m venv venv
```

Activar entorno:

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar variables de entorno:

```env
SECRET_KEY=tu_clave
DATABASE_URL=postgresql://usuario:password@host/database
MAIL_USERNAME=correo
MAIL_PASSWORD=password
```

Ejecutar:

```bash
python app.py
```

---

## Estructura del Proyecto

```text
control_gastos/
│
├── app.py
├── config.py
├── requirements.txt
│
├── models/
├── routes/
├── services/
├── templates/
├── static/
│
└── migrations/
```

---

## Seguridad

- Contraseñas cifradas con Werkzeug
- Sesiones protegidas
- Acceso restringido por usuario
- Panel administrativo protegido

---

## SEO

- Sitemap XML
- Robots.txt
- Open Graph
- Dominio personalizado

---

## Autor

Cortes Software

Desarrollado por William Cortes.

---

## Licencia

Proyecto desarrollado con fines educativos y comerciales.