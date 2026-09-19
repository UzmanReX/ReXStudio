from flask import Flask, render_template
import os
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)


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


@app.route("/test-mail")
def test_mail():
    gmail = os.environ["GMAIL_ADRESI"]
    app_password = os.environ["GMAIL_UYGULAMA_SIFRESI"]
    alici = os.environ["TEST_ALICI"]

    mesaj = MIMEText(
        """Merhaba!

Bu ReXStudio test mailidir.

Gmail kod gönderme sistemi çalışıyor.
""",
        "plain",
        "utf-8"
    )

    mesaj["Subject"] = "ReXStudio Test"
    mesaj["From"] = gmail
    mesaj["To"] = alici

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail, app_password)
        server.send_message(mesaj)

    return "Mail başarıyla gönderildi!"


if __name__ == "__main__":
    app.run(debug=True)
