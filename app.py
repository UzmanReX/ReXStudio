from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory, abort, make_response
from datetime import timedelta
import os
import secrets
import time
import sqlite3
import requests
import uuid


app = Flask(__name__, static_folder=None)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "rexstudio-development-secret"
)

app.permanent_session_lifetime = timedelta(days=30)

DATABASE = "users.db"
ADMIN_PASSWORD = "12555564"

GMAIL_SCRIPT_URL = os.environ.get("GMAIL_SCRIPT_URL")
GMAIL_SCRIPT_SECRET = os.environ.get("GMAIL_SCRIPT_SECRET")


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            name TEXT NOT NULL,
            filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS site_stats (
            id INTEGER PRIMARY KEY,
            total_visits INTEGER NOT NULL DEFAULT 0,
            unique_visitors INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS download_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT UNIQUE NOT NULL,
            download_count INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.execute("""
        INSERT OR IGNORE INTO site_stats
        (id, total_visits, unique_visitors)
        VALUES (1, 0, 0)
    """)

    for app_name in [
        "UzmanNotPro.exe",
        "UzmanNotProMax.exe",
        "ReX.Launcher.exe"
    ]:
        conn.execute("""
            INSERT OR IGNORE INTO download_stats
            (app_name, download_count)
            VALUES (?, 0)
        """, (app_name,))

    conn.commit()
    conn.close()


init_db()


# =========================================================
# MAIL
# =========================================================

def send_code(email, code):

    if not GMAIL_SCRIPT_URL:
        return False, "GMAIL_SCRIPT_URL bulunamadı."

    if not GMAIL_SCRIPT_SECRET:
        return False, "GMAIL_SCRIPT_SECRET bulunamadı."

    try:

        response = requests.post(
            GMAIL_SCRIPT_URL,
            json={
                "secret": GMAIL_SCRIPT_SECRET,
                "email": email,
                "code": code
            },
            timeout=30
        )

        try:
            data = response.json()

        except ValueError:
            return False, "Google Apps Script geçersiz yanıt verdi."

        if data.get("success") is True:
            return True, "OK"

        return False, data.get(
            "error",
            "Mail gönderilemedi."
        )

    except requests.RequestException as e:
        return False, f"Bağlantı hatası: {e}"

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# =========================================================
# SITE STATS
# =========================================================

def count_visit():

    visitor_id = request.cookies.get("rex_visitor_id")
    new_visitor = False

    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        new_visitor = True

    conn = get_db()

    conn.execute("""
        UPDATE site_stats
        SET total_visits = total_visits + 1
        WHERE id = 1
    """)

    if new_visitor:

        try:

            conn.execute(
                "INSERT INTO visitors (visitor_id) VALUES (?)",
                (visitor_id,)
            )

            conn.execute("""
                UPDATE site_stats
                SET unique_visitors = unique_visitors + 1
                WHERE id = 1
            """)

        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()

    return visitor_id, new_visitor


def page(template, **kwargs):

    visitor_id, new_visitor = count_visit()

    response = make_response(
        render_template(template, **kwargs)
    )

    if new_visitor:

        response.set_cookie(
            "rex_visitor_id",
            visitor_id,
            max_age=31536000,
            httponly=True,
            samesite="Lax"
        )

    return response


# =========================================================
# DOWNLOAD STATS
# =========================================================

def record_download(app_name):

    conn = get_db()

    conn.execute("""
        INSERT OR IGNORE INTO download_stats
        (app_name, download_count)
        VALUES (?, 0)
    """, (app_name,))

    conn.execute("""
        UPDATE download_stats
        SET download_count = download_count + 1
        WHERE app_name = ?
    """, (app_name,))

    conn.commit()
    conn.close()


# =========================================================
# STATIC
# =========================================================

@app.route("/static/<path:filename>")
def static_files(filename):

    return send_from_directory(
        os.path.join(app.root_path, "static"),
        filename
    )


# =========================================================
# MAIN PAGES
# =========================================================

@app.route("/")
def home():

    if session.get("logged_in") and session.get("remember_login"):
        return redirect(url_for("hesap"))

    return page("index.html")


@app.route("/anasayfa")
def anasayfa():
    return page("index.html")


@app.route("/uygulamalar")
def uygulamalar():
    return page("uygulama.html")


@app.route("/projeler")
def projeler():
    return page("projeler.html")


@app.route("/destek")
def destek():
    return page("destek.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/kayit", methods=["GET", "POST"])
def kayit():

    if session.get("logged_in"):
        return redirect(url_for("hesap"))

    if request.method == "GET":
        return page("register.html")

    username = request.form.get(
        "username",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    if not username or not email:
        return render_template(
            "register.html",
            error="Kullanıcı adı ve e-posta zorunludur."
        )
