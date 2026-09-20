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

    conn.execute("""
        INSERT OR IGNORE INTO download_stats
        (app_name, download_count)
        VALUES ('UzmanNotPro.exe', 0)
    """)

    conn.execute("""
        INSERT OR IGNORE INTO download_stats
        (app_name, download_count)
        VALUES ('UzmanNotProMax.exe', 0)
    """)

    conn.commit()
    conn.close()


init_db()


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

        return False, data.get("error", "Mail gönderilemedi.")

    except requests.RequestException as e:
        return False, f"Bağlantı hatası: {e}"

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


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


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        filename
    )


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


@app.route("/kayit", methods=["GET", "POST"])
def kayit():

    if session.get("logged_in"):
        return redirect(url_for("hesap"))

    if request.method == "GET":
        return page("register.html")

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
        "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
        (username,)
    ).fetchone()

    existing_email = conn.execute(
        "SELECT id FROM users WHERE LOWER(email) = LOWER(?)",
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

    return redirect(url_for("dogrula"))


@app.route("/dogrula", methods=["GET", "POST"])
def dogrula():

    if "register_code" not in session:
        return redirect(url_for("kayit"))

    if request.method == "GET":
        return page("verify.html")

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

    session.clear()

    session.permanent = True
    session["logged_in"] = True
    session["username"] = username
    session["remember_login"] = True
    session["is_admin"] = False
    session["toast"] = "Kayıt olundu"

    return redirect(url_for("hesap"))


@app.route("/giris", methods=["GET", "POST"])
def giris():

    if request.method == "GET":

        if session.get("logged_in"):
            return redirect(url_for("hesap"))

        return page("login.html")

    if session.get("logged_in"):
        return redirect(url_for("hesap"))

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    remember = request.form.get("remember") == "on"

    if not username or not email:
        return render_template(
            "login.html",
            error="Kullanıcı adı ve Gmail alanları zorunludur."
        )

    if not email.endswith("@gmail.com"):
        return render_template(
            "login.html",
            error="Lütfen geçerli bir Gmail adresi kullanın."
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE LOWER(username) = LOWER(?)
        AND LOWER(email) = LOWER(?)
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

    session["login_username"] = user["username"]
    session["login_email"] = user["email"]
    session["login_code"] = code
    session["login_code_time"] = time.time()
    session["login_remember"] = remember

    success, message = send_code(user["email"], code)

    if not success:
        session.clear()

        return render_template(
            "login.html",
            error=f"Mail gönderilemedi: {message}"
        )

    return redirect(url_for("login_dogrula"))


@app.route("/login-dogrula", methods=["GET", "POST"])
def login_dogrula():

    if "login_code" not in session:
        return redirect(url_for("giris"))

    if request.method == "GET":
        return page("login_verify.html")

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

    session.permanent = remember
    session["logged_in"] = True
    session["username"] = username
    session["remember_login"] = remember
    session["is_admin"] = False
    session["toast"] = "Giriş yapıldı"

    return redirect(url_for("hesap"))


@app.route("/hesap")
def hesap():

    if not session.get("logged_in"):
        return redirect(url_for("giris"))

    username = session.get("username")

    conn = get_db()

    user = conn.execute(
        """
        SELECT username, email
        FROM users
        WHERE LOWER(username) = LOWER(?)
        """,
        (username,)
    ).fetchone()

    apps = conn.execute(
        """
        SELECT name, filename, created_at
        FROM apps
        WHERE LOWER(username) = LOWER(?)
        ORDER BY id DESC
        """,
        (username,)
    ).fetchall()

    conn.close()

    if not user:
        session.clear()
        return redirect(url_for("giris"))

    toast = session.pop("toast", None)

    return render_template(
        "account.html",
        username=user["username"],
        email=user["email"],
        apps=apps,
        is_admin=session.get("is_admin", False),
        toast=toast
    )


@app.route("/yonetici-giris", methods=["GET", "POST"])
def yonetici_giris():

    if not session.get("logged_in"):
        return redirect(url_for("giris"))

    if session.get("is_admin"):
        return redirect(url_for("yonetici"))

    if request.method == "GET":
        return render_template("admin_login.html")

    password = request.form.get("password", "")

    if password != ADMIN_PASSWORD:
        return render_template(
            "admin_login.html",
            error="Yönetici şifresi yanlış."
        )

    session["is_admin"] = True
    session["toast"] = "Yönetici olarak giriş yapıldı."

    return redirect(url_for("yonetici"))


@app.route("/yonetici")
def yonetici():

    if not session.get("logged_in"):
        return redirect(url_for("giris"))

    if not session.get("is_admin"):
        abort(403)

    conn = get_db()

    users = conn.execute(
        """
        SELECT username, created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    stats = conn.execute(
        """
        SELECT total_visits, unique_visitors
        FROM site_stats
        WHERE id = 1
        """
    ).fetchone()

    download_stats = conn.execute(
        """
        SELECT app_name, download_count
        FROM download_stats
        ORDER BY download_count DESC
        """
    ).fetchall()

    total_downloads = conn.execute(
        """
        SELECT COALESCE(SUM(download_count), 0)
        FROM download_stats
        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        stats=stats,
        download_stats=download_stats,
        total_downloads=total_downloads
    )


@app.route("/indir/uzmannotpromax")
def indir_uzmannotpromax():

    if not session.get("logged_in"):
        abort(403)

    downloads_folder = os.path.join(
        app.root_path,
        "downloads"
    )

    file_path = os.path.join(
        downloads_folder,
        "UzmanNotProMax.exe"
    )

    if not os.path.isfile(file_path):
        abort(404)

    record_download("UzmanNotProMax.exe")

    return send_from_directory(
        downloads_folder,
        "UzmanNotProMax.exe",
        as_attachment=True,
        download_name="UzmanNotProMax.exe"
    )


@app.route("/indir/uzmannot")
def indir_uzmannot():

    downloads_folder = os.path.join(
        app.root_path,
        "static"
    )

    file_path = os.path.join(
        downloads_folder,
        "UzmanNotPro.exe"
    )

    if not os.path.isfile(file_path):
        abort(404)

    record_download("UzmanNotPro.exe")

    return send_from_directory(
        downloads_folder,
        "UzmanNotPro.exe",
        as_attachment=True,
        download_name="UzmanNotPro.exe"
    )


@app.route("/cikis")
def cikis():
    session.clear()
    return redirect(url_for("anasayfa"))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
