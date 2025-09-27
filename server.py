import os
import sqlite3
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, request, render_template, make_response
from werkzeug.security import generate_password_hash, check_password_hash


# Configuración de la aplicación
DB_PATH = os.environ.get("APP_DB_PATH", "app.db")


# Crear instancia de la aplicación Flask
# __name__ permite a Flask localizar recursos relativos (templates, static, etc.)
app = Flask(__name__)


# Acceso y esquema de la base de datos
# sqlite3 de la standard library.
# La tabla 'usuarios' almacenará usuarios con contraseña hasheada.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_db_connection() -> sqlite3.Connection:
    """Obtiene una conexión nueva a la base de datos.
    Se crea por operación para evitar problemas de uso concurrente.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Retornar filas como tuplas
        return conn
    except sqlite3.Error as e:
        # Se podría loguear y levantar un error más específico
        raise RuntimeError(f"No se pudo abrir la base de datos en {DB_PATH}: {e}")


def init_db() -> None:
    """Inicializa la base de datos creando la tabla 'usuarios' si no existe.
    Estructura:
      - id: PK autoincremental
      - usuario: nombre único
      - password_hash: hash de la contraseña
      - created_at: timestamp
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(SCHEMA_SQL)
        conn.commit()
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# Sirve para validar que la app corre y la DB está inicializada.
@app.get("/")
def root_status():
    # Respuesta sencilla para probar el arranque de la API
    return jsonify({"status": "ok", "message": "API anda bien :)"})


# Helper de autenticación básica
def verify_basic_auth(username: str, password: str) -> bool:
    """Verifica credenciales (usuario/password) contra la DB usando el hash almacenado.
    Retorna True si son válidas, False en si no.
    """
    if not username or not password:
        return False
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT password_hash FROM usuarios WHERE usuario = ?", (username,))
        row = cur.fetchone()
        if row is None:
            return False
        return check_password_hash(row[0], password)
    except sqlite3.Error:
        # Devuelve False ante errores de DB
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# GET /tareas
# Requiere Autenticación Básica. Si las credenciales son válidas, renderiza una plantilla HTML.
@app.get("/tareas")
def tareas():
    # Flask parsea el header Authorization automáticamente en request.authorization
    auth = request.authorization
    if not auth or not verify_basic_auth(auth.username, auth.password):
        # Responde 401 e indica el esquema de autenticación requerido
        resp = make_response(jsonify({"error": "autenticación requerida"}), 401)  # en realidad se ve así: {"error": "autenticaci\u00f3n requerida"}, debe estar en portugués
        resp.headers["WWW-Authenticate"] = 'Basic realm="tareas"'
        return resp

    # Credenciales válidas, renderiza la plantilla
    return render_template("tareas.html", usuario=auth.username)


# POST /registro
# Recibe JSON: {"usuario": "nombre", "password": "1234"}
# Valida campos, hashea el password y guarda en SQLite.
@app.post("/registro")
def registro():
    conn: Optional[sqlite3.Connection] = None
    try:
        data = (request.get_json(silent=True) or {})
        usuario = (data.get("usuario") or "").strip() # como mínimo, obvio acá debería ir un buen regex
        password = (data.get("password") or "")

        # Validaciones de entrada
        if not usuario or not password:
            return jsonify({"error": "faltan campos"}), 400

        # Hash de la contraseña
        password_hash = generate_password_hash(password)

        # Guarda en DB
        conn = get_db_connection()
        cur = conn.cursor()
        created_at = datetime.now().isoformat(timespec="seconds")
        cur.execute(
            "INSERT INTO usuarios (usuario, password_hash, created_at) VALUES (?, ?, ?)",
            (usuario, password_hash, created_at),
        )  # Como usamos consultas parametrizadas en todos los puntos donde entra input del usuario, SQLite trata el contenido como datos y no como parte del SQL (y evita inyección aunque te envíen comillas, OR 1=1, etc.).
        conn.commit()

        return jsonify({"mensaje": "usuario creado", "usuario": usuario}), 201
    except sqlite3.IntegrityError:
        # Error unicidad (usuario ya existe)
        return jsonify({"error": "usuario ya existe"}), 409
    except sqlite3.Error:
        # Errores generales de SQLite
        return jsonify({"error": "error de base de datos"}), 500
    except Exception:
        # Cualquier otro error inesperado
        return jsonify({"error": "error inesperado"}), 500
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# POST /login
# Recibe JSON: {"usuario": "nombre", "password": "1234"}
# Verifica credenciales comparando el hash almacenado.
@app.post("/login")
def login():
    conn: Optional[sqlite3.Connection] = None
    try:
        data = (request.get_json(silent=True) or {})
        usuario = (data.get("usuario") or "").strip()
        password = (data.get("password") or "")

        # Validaciones simples
        if not usuario or not password:
            return jsonify({"error": "faltan campos"}), 400

        # Buscar usuario en la DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM usuarios WHERE usuario = ?", (usuario,))
        row = cur.fetchone()
        if row is None:
            # Usuario no existe
            return jsonify({"error": "credenciales inválidas"}), 401  # {"error": "credenciales inv\u00e1lidas"}

        _user_id, password_hash = row
        if not check_password_hash(password_hash, password):
            # Password incorrecto
            return jsonify({"error": "credenciales inválidas"}), 401

        # OK
        return jsonify({"mensaje": "login ok", "usuario": usuario}), 200
    except sqlite3.Error:
        return jsonify({"error": "error de base de datos"}), 500
    except Exception:
        return jsonify({"error": "error inesperado"}), 500
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# Cuando corremos "python server.py" se inicializa la DB y se levanta el servidor.
if __name__ == "__main__":
    # Inicializar base de datos antes de iniciar el servidor HTTP
    init_db()

    # Levantar servidor de desarrollo
    # host=127.0.0.1 limita el acceso a la máquina local.
    # Cambiar port si el 5000 está ocupado por otro proceso.
    app.run(host="127.0.0.1", port=5000, debug=True)
