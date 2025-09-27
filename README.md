# Gestión de Tareas con API y DB (Flask + SQLite)

API REST con Flask, SQLite y Basic Auth.

## Requisitos
- Python 3.8+
- Flask

Instalación rápida:

```bash
# (Opcional) Crear y activar venv
python -m venv .venv
# Git Bash
source .venv/Scripts/activate
# CMD/PowerShell
# .venv\Scripts\activate

# Instalar Flask
pip install flask
```

## Ejecutar el servidor

```bash
python server.py
```

El servidor levanta en: http://127.0.0.1:5000/

## Endpoints y pruebas

### 1) POST /registro
Crear un usuario con contraseña (almacenada hasheada en SQLite).

```bash
curl -X POST "http://127.0.0.1:5000/registro" \
  -H "Content-Type: application/json" \
  -d '{"usuario":"fulanito","password":"1234"}'
```

Respuestas esperadas:
- 201: `{ "mensaje": "usuario creado", "usuario": "fulanito" }`
- 409: `{ "error": "usuario ya existe" }` (si repetimos el usuario)
- 400: `{ "error": "faltan campos" }` (si falta usuario o password)

### 2) POST /login
Verifica credenciales contra el hash almacenado.

```bash
curl -X POST "http://127.0.0.1:5000/login" \
  -H "Content-Type: application/json" \
  -d '{"usuario":"fulanito","password":"1234"}'
```

Respuestas esperadas:
- 200: `{ "mensaje": "login ok", "usuario": "fulanito" }`
- 401: `{ "error": "credenciales inválidas" }` (usuario inexistiente o password incorrecto)
- 400: `{ "error": "faltan campos" }`

### 3) GET /tareas
Ruta protegida con Autenticación Básica. Si las credenciales son válidas, devuelve HTML de bienvenida (plantilla `templates/tareas.html`).

```bash
curl -u fulanito:1234 "http://127.0.0.1:5000/tareas"
```

Respuestas esperadas:
- 200: HTML con “Bienvenido/a, fulanito …”
- 401: `{ "error": "autenticación requerida" }` si no se envían credenciales o son inválidas.

## Estructura del proyecto

- `server.py`: API Flask con endpoints `/registro`, `/login`, `/tareas` y SQLite.
- `templates/tareas.html`: plantilla HTML del área de tareas.
- `app.db`: base de datos SQLite (se crea automáticamente).
