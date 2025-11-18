# backend/app.py
from flask import Flask, request, jsonify, g
import os
import mysql.connector
from mysql.connector import Error, pooling
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)

# Config (envs with sensible defaults)
DB_HOST = os.getenv("MYSQL_HOST", "db")
DB_USER = os.getenv("MYSQL_USER", "user")
DB_PASS = os.getenv("MYSQL_PASSWORD", "password")
DB_NAME = os.getenv("MYSQL_DATABASE", "myappdb")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = int(os.getenv("JWT_EXP_SECONDS", 3600))

# Setup a connection pool for efficiency
POOL_NAME = "mypool"
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
try:
    cnxpool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name=POOL_NAME,
        pool_size=POOL_SIZE,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
except Exception as e:
    app.logger.error("Failed to create DB pool: %s", e)
    cnxpool = None

def get_db_connection():
    if cnxpool is None:
        raise Error("DB pool not initialized")
    return cnxpool.get_connection()

def log_action(user_id, action):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (user_id, action) VALUES (%s, %s)", (user_id, action))
        conn.commit()
    except Exception as e:
        app.logger.error("Failed to write log: %s", e)
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # expect Authorization: Bearer <token>
        auth = request.headers.get("Authorization", None)
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.current_user = {"id": payload.get("user_id"), "name": payload.get("name")}
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception as e:
            app.logger.error("JWT decode error: %s", e)
            return jsonify({"error": "Token is invalid"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Two-Tier Web App (Flask)"}), 200

# Register - creates user with hashed password
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400

    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
            (name, email, phone, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        log_action(user_id, "register")
        return jsonify({"status": "created", "id": user_id, "name": name, "email": email}), 201
    except Error as e:
        app.logger.error("Register error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

# Login - returns JWT
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email and password required"}), 400
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, password_hash FROM users WHERE email=%s LIMIT 1", (email,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "invalid credentials"}), 401
        if not check_password_hash(row["password_hash"], password):
            return jsonify({"error": "invalid credentials"}), 401

        payload = {
            "user_id": row["id"],
            "name": row["name"],
            "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return jsonify({"token": token, "user": {"id": row["id"], "name": row["name"]}})
    except Error as e:
        app.logger.error("Login error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

# Example protected route
@app.route("/profile", methods=["GET"])
@token_required
def profile():
    return jsonify({"user": g.current_user}), 200

# Get single user
@app.route("/user/<int:user_id>", methods=["GET"])
def get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, phone, created_at FROM users WHERE id=%s", (user_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "user not found"}), 404
        return jsonify(row)
    except Error as e:
        app.logger.error("Get user error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

def update_user(user_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    phone = data.get("phone")

    params = []
    if name is not None:
        updates.append("name=%s"); params.append(name)
        updates.append("email=%s"); params.append(email)
    if phone is not None:
        updates.append("phone=%s"); params.append(phone)
        pw_hash = generate_password_hash(password)
        updates.append("password_hash=%s"); params.append(pw_hash)
    if not updates:
        return jsonify({"error": "no fields to update"}), 400

    params.append(user_id)
    sql = "UPDATE users SET " + ", ".join(updates) + " WHERE id=%s"
    try:
        conn = get_db_connection()
        cursor.execute(sql, tuple(params))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "user not found"}), 404
        log_action(user_id, "update")
        return jsonify({"status": "updated", "id": user_id})
    except Error as e:
        app.logger.error("Update error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

# Delete user
@app.route("/user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "user not found"}), 404
        log_action(user_id, "delete")
        return jsonify({"status": "deleted", "id": user_id})
    except Error as e:
        app.logger.error("Delete error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

# List users with pagination and search
@app.route("/users", methods=["GET"])
def list_users():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        limit = max(min(int(request.args.get("limit", 10)), 100), 1)
    except ValueError:
        return jsonify({"error": "invalid pagination params"}), 400

    search = (request.args.get("search") or "").strip()

    offset = (page - 1) * limit
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if search:
            like = f"%{search}%"
            cursor.execute(
                "SELECT id, name, email, phone, created_at FROM users WHERE name LIKE %s OR email LIKE %s ORDER BY id DESC LIMIT %s OFFSET %s",
                (like, like, limit, offset)
            )
        else:
            cursor.execute(
                "SELECT id, name, email, phone, created_at FROM users ORDER BY id DESC LIMIT %s OFFSET %s",
                (limit, offset)
            )
        rows = cursor.fetchall()

        # total count (for client to know total pages)
        if search:
            cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE name LIKE %s OR email LIKE %s", (like, like))
        else:
            cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total = cursor.fetchone()["cnt"]

        return jsonify({"page": page, "limit": limit, "total": total, "users": rows})
    except Error as e:
        app.logger.error("List users error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

# View logs (simple)
@app.route("/logs", methods=["GET"])
def view_logs():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, user_id, action, timestamp FROM logs ORDER BY id DESC LIMIT 200")
        rows = cursor.fetchall()
        return jsonify(rows)
    except Error as e:
        app.logger.error("Logs error: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except:
            pass

if __name__ == "__main__":
    # for local dev; in docker we use gunicorn
    app.run(host="0.0.0.0", port=5000)
        cursor = conn.cursor()

    if password is not None and password != "":
    if email is not None:
    updates = []
    password = data.get("password")
    email = data.get("email")
@app.route("/user/<int:user_id>", methods=["PUT"])

