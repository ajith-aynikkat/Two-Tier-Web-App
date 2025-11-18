from flask import Flask, request, jsonify
import os
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)

DB_HOST = os.getenv("MYSQL_HOST", "db")
DB_USER = os.getenv("MYSQL_USER", "user")
DB_PASS = os.getenv("MYSQL_PASSWORD", "password")
DB_NAME = os.getenv("MYSQL_DATABASE", "myappdb")

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME
        )
        return conn
    except Error as e:
        app.logger.error(f"DB connection error: {e}")
        raise

@app.route("/")
def index():
    return "Two-Tier Web App (Flask) — OK"

@app.route("/users", methods=["GET"])
def users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM users ORDER BY id DESC LIMIT 100;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(rows)

@app.route("/create_user", methods=["POST"])
def create_user():
    data = request.get_json(silent=True) or {}
    name = data.get("name") or data.get("username") or "anonymous"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name) VALUES (%s);", (name,))
    conn.commit()
    user_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return jsonify({"status": "created", "id": user_id, "name": name}), 201

if __name__ == "__main__":
    # use 0.0.0.0 so container binds to external host
    app.run(host="0.0.0.0", port=5000)
