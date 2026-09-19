from flask import Flask, render_template, request, session, redirect, url_for
import os
import random
import time
import sqlite3
import requests

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "rexstudio-test-secret")

DATABASE = "users.db"


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
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


init_db()


def send_code(email, code):
    api_key = os.environ.get("RESEND_API_KEY")

    if not api_key:
        return False, "RESEND_API_KEY bulunamadı."

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "onboarding@resend.dev",
                "to": [email],
                "subject": "ReXStudio Doğrulama Kodunuz",
                "text": f"""Merhaba!

ReXStudio doğrulama kodunuz:

{code}

Bu kod 10 dakika boyunca geçerlidir.

Kodu siz istemediyseniz bu e-postayı dikkate almayın.

ReXStudio"""
            },
            timeout=15
        )

        if response.status_code in [200, 201]:
            return True, "OK"

        return False, response.text

    except Exception as e:
        return False, str(e)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/uygulamalar")
def uygulamalar():
    return render_template("uygulama.html")


@app.route("/projeler")
def projeler():
    return render_template("projeler.html")


@app.route("/destek")
def destek():
    return render_template("destek.html")


@app.route("/kayit", methods=["GET", "POST"])
def kayit():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not username or not email:
        return "Kullanıcı adı ve Gmail zorunludur."

    if not email.endswith("@gmail.com"):
        return "Lütfen Gmail adresi kullanın."

    conn = get_db()

    existing_user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username, email)
    ).fetchone()

    conn.close()

    if existing_user:
        return "Bu kullanıcı adı veya Gmail zaten kayıtlı."

    code = str(random.randint(100000, 999999))

    session["register_username"] = username
    session["register_email"] = email
    session["register_code"] = code
    session["register_code_time"] = time.time()

    success, message = send_code(email, code)

    if not success:
        session.clear()
        return f"Mail gönderilemedi: {message}"

    return redirect(url_for("dogrula"))


@app.route("/dogrula", methods=["GET", "POST"])
def dogrula():

    if "register_code" not in session:
        return redirect(url_for("kayit"))

    if request.method == "GET":
        return render_template("verify.html")

    entered_code = request.form.get("code", "").strip()

    saved_code = session.get("register_code")
    code_time = session.get("register_code_time")

    if not code_time or time.time() - code_time > 600:
        session.clear()
        return "Kodun süresi doldu. Lütfen tekrar kayıt olun."

    if entered_code != saved_code:
        return "Kod yanlış!"

    username = session["register_username"]
    email = session["register_email"]

    conn = get_db()

    try:
        conn.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            (username, email)
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        session.clear()
        return "Bu kullanıcı zaten kayıtlı."

    conn.close()

    session.clear()

    return "Kayıt başarılı! Artık giriş yapabilirsiniz."


@app.route("/giris", methods=["GET", "POST"])
def giris():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not username or not email:
        return "Kullanıcı adı ve Gmail zorunludur."

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ? AND email = ?",
        (username, email)
    ).fetchone()

    conn.close()

    if not user:
        return "Kullanıcı adı veya Gmail yanlış."

    code = str(random.randint(100000, 999999))

    session["login_username"] = username
    session["login_email"] = email
    session["login_code"] = code
    session["login_code_time"] = time.time()

    success, message = send_code(email, code)

    if not success:
        session.clear()
        return f"Mail gönderilemedi: {message}"

    return redirect(url_for("login_dogrula"))


@app.route("/login-dogrula", methods=["GET", "POST"])
def login_dogrula():

    if "login_code" not in session:
        return redirect(url_for("giris"))

    if request.method == "GET":
        return render_template("login_verify.html")

    entered_code = request.form.get("code", "").strip()

    saved_code = session.get("login_code")
    code_time = session.get("login_code_time")

    if not code_time or time.time() - code_time > 600:
        session.clear()
        return "Kodun süresi doldu. Lütfen tekrar giriş yapın."

    if entered_code != saved_code:
        return "Kod yanlış!"

    username = session["login_username"]

    session.clear()

    session["logged_in"] = True
    session["username"] = username

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
