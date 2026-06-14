# Control de Gastos Personales

Aplicación web desarrollada con Flask para la administración de finanzas personales.

Permite registrar ingresos y gastos, visualizar reportes, generar archivos Excel y PDF, además de mostrar estadísticas mediante gráficos interactivos.

---

## Características

### Autenticación

- Registro de usuarios
- Inicio de sesión
- Cierre de sesión
- Protección de rutas mediante sesiones

### Gestión de Ingresos

- Registrar ingresos
- Editar ingresos
- Eliminar ingresos
- Historial de ingresos

### Gestión de Gastos

- Registrar gastos
- Editar gastos
- Eliminar gastos
- Clasificación por categorías

### Dashboard

- Total de ingresos
- Total de gastos
- Balance general
- Gráfico Ingresos vs Gastos
- Gráfico Gastos por Categoría

### Reportes

- Exportación a Excel (.xlsx)
- Exportación a PDF (.pdf)

### Validaciones

- Campos obligatorios
- Montos mayores a cero
- Protección de acceso por usuario

---

## Tecnologías Utilizadas

### Backend

- Python 3
- Flask
- SQLAlchemy
- SQLite

### Frontend

- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- Chart.js

### Reportes

- OpenPyXL
- ReportLab

---

## Estructura del Proyecto

```text
control_gastos/
│
├── app.py
├── config.py
├── requirements.txt
├── README.md
│
├── database/
│
├── models/
│   ├── user.py
│   ├── income.py
│   └── expense.py
│
├── routes/
│   └── auth_routes.py
│
├── services/
│
├── static/
│
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── incomes.html
    ├── expenses.html
    └── reports.html
```

---

## Instalación

### 1. Clonar repositorio

```bash
git clone URL_DEL_REPOSITORIO
```

### 2. Ingresar al proyecto

```bash
cd control_gastos
```

### 3. Crear entorno virtual

```bash
python -m venv venv
```

### 4. Activar entorno virtual

Windows:

```bash
venv\Scripts\activate
```

Linux / Mac:

```bash
source venv/bin/activate
```

### 5. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 6. Ejecutar aplicación

```bash
python app.py
```

---

## Acceso Local

La aplicación estará disponible en:

```text
http://127.0.0.1:5000
```

---

## Funcionalidades Implementadas

| Módulo | Estado |
|----------|----------|
| Registro | ✅ |
| Login | ✅ |
| Dashboard | ✅ |
| Ingresos | ✅ |
| Gastos | ✅ |
| Reportes Excel | ✅ |
| Reportes PDF | ✅ |
| Chart.js | ✅ |
| Validaciones | ✅ |

---

## Mejoras Futuras

- Validación avanzada de correo electrónico
- Confirmación de cuenta por email
- Recuperación de contraseña
- Presupuestos mensuales
- Metas de ahorro
- Dashboard avanzado
- Integración con Power BI
- Despliegue en Render

---

## Autor

William Cortes

Proyecto desarrollado como práctica profesional para fortalecer conocimientos en:

- Flask
- SQLAlchemy
- SQLite
- Bootstrap
- Git
- GitHub
- Reportes PDF y Excel
- Visualización de datos con Chart.js

---

## Licencia

Proyecto de uso educativo.