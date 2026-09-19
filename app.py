```python
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import timedelta
import os
import secrets
import time
import sqlite3
import requests

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "rexstudio-development-secret"
)

# Beni Hatırla seçilirse oturum 30 gün kalır
app.permanent_session_lifetime = timedelta(days=30)

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

ReXStudio
Gönderen: onboarding@resend.dev"""
            },
            timeout=15
        )

        if response.status_code in (200, 201):
            return True, "OK"

        return False, response.text

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# =========================
# ANA SAYFA
# =========================

@app.route("/")
def home():

    # Giriş yapılmışsa otomatik Hesabım
    if session.get("logged_in"):
        return redirect(url_for("hesap"))

    return render_template("index.html")


# =========================
# DİĞER SAYFALAR
# =========================

@app.route("/uygulamalar")
def uygulamalar():
    return render_template("uygulama.html")


@app.route("/projeler")
def projeler():
    return render_template("projeler.html")


@app.route("/destek")
def destek():
    return render_template("destek.html")


# =========================
# KAYIT
# =========================

@app.route("/kayit", methods=["GET", "POST"])
def kayit():

    if session.get("logged_in"):
        return redirect(url_for("hesap"))

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not username or not email:
        return render_template(
            "register.html",
            error="Kullanıcı adı ve Gmail alanları zorunludur."
        )

    if not email.endswith("@gmail.com"):
        return render_template(
            "register.html",
            error="Lütfen geçerli bir Gmail adresi kullanın."
        )

    if len(username) < 3:
        return render_template(
            "register.html",
            error="Kullanıcı adı en az 3 karakter olmalıdır."
        )

    conn = get_db()

    existing_username = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    existing_email = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    conn.close()

    if existing_username:
        return render_template(
            "register.html",
            error="Bu kullanıcı adı zaten kullanılıyor."
        )

    if existing_email:
        return render_template(
            "register.html",
            error="Bu Gmail adresi zaten kayıtlı."
        )

    code = str(secrets.randbelow(900000) + 100000)

    session["register_username"] = username
    session["register_email"] = email
    session["register_code"] = code
    session["register_code_time"] = time.time()

    success, message = send_code(email, code)

    if not success:
        session.clear()

        return render_template(
            "register.html",
            error=f"Mail gönderilemedi: {message}"
        )

    return render_template(
        "verify.html",
        success=f"Doğrulama kodu {email} adresine gönderildi."
    )


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

        return render_template(
            "register.html",
            error="Kodun süresi doldu. Lütfen tekrar kayıt olun."
        )

    if entered_code != saved_code:
        return render_template(
            "verify.html",
            error="Kod yanlış. Lütfen tekrar kontrol edin."
        )

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

        return render_template(
            "register.html",
            error="Bu kullanıcı adı veya Gmail zaten kayıtlı."
        )

    conn.close()

    session.pop("register_code", None)
    session.pop("register_code_time", None)
    session.pop("register_username", None)
    session.pop("register_email", None)

    return render_template(
        "verify.html",
        success="Kayıt başarılı! Hesabınız oluşturuldu.",
        registered=True
    )


# =========================
# GİRİŞ
# =========================

@app.route("/giris", methods=["GET", "POST"])
def giris():

    if session.get("logged_in"):
        return redirect(url_for("hesap"))

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()

    remember = request.form.get("remember") == "on"

    if not username or not email:
        return render_template(
            "login.html",
            error="Kullanıcı adı ve Gmail alanları zorunludur."
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT * FROM users
        WHERE username = ? AND email = ?
        """,
        (username, email)
    ).fetchone()

    conn.close()

    if not user:
        return render_template(
            "login.html",
            error="Kullanıcı adı veya Gmail yanlış."
        )

    code = str(secrets.randbelow(900000) + 100000)

    session["login_username"] = username
    session["login_email"] = email
    session["login_code"] = code
    session["login_code_time"] = time.time()
    session["login_remember"] = remember

    success, message = send_code(email, code)

    if not success:
        session.clear()

        return render_template(
            "login.html",
            error=f"Mail gönderilemedi: {message}"
        )

    return render_template(
        "login_verify.html",
        success=f"Giriş kodu {email} adresine gönderildi."
    )


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

        return render_template(
            "login.html",
            error="Kodun süresi doldu. Lütfen tekrar giriş yapın."
        )

    if entered_code != saved_code:
        return render_template(
            "login_verify.html",
            error="Kod yanlış. Lütfen tekrar kontrol edin."
        )

    username = session["login_username"]
    remember = session.get("login_remember", False)

    session.clear()

    session["logged_in"] = True
    session["username"] = username

    # Beni Hatırla
    session.permanent = remember

    return render_template(
        "login_verify.html",
        success=f"Giriş başarılı! Hoş geldin, {username}.",
        logged_in=True
    )


# =========================
# HESAP
# =========================

@app.route("/hesap")
def hesap():

    if not session.get("logged_in"):
        return redirect(url_for("giris"))

    username = session.get("username")

    conn = get_db()

    user = conn.execute(
        "SELECT username, email FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    apps = conn.execute(
        """
        SELECT name, filename, created_at
        FROM apps
        WHERE username = ?
        ORDER BY id DESC
        """,
        (username,)
    ).fetchall()

    conn.close()

    if not user:
        session.clear()
        return redirect(url_for("giris"))

    return render_template(
        "account.html",
        username=user["username"],
        email=user["email"],
        apps=apps
    )


# =========================
# ÇIKIŞ
# =========================

@app.route("/cikis")
def cikis():

    session.clear()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
```
