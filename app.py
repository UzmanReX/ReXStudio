from flask import Flask, render_template
import os
import requests

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
    api_key = os.environ.get("RESEND_API_KEY")

    if not api_key:
        return "RESEND_API_KEY bulunamadı!", 500

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "from": "onboarding@resend.dev",
                "to": ["galatasaray01efe@gmail.com"],
                "subject": "ReXStudio Test Maili",
                "text": """Merhaba!

Bu ReXStudio test mailidir.

Resend API üzerinden başarıyla gönderildi."""
            },
            timeout=15
        )

        if response.status_code in [200, 201]:
            return "Mail başarıyla gönderildi!"

        return f"Resend hata verdi: {response.status_code} - {response.text}", 500

    except Exception as e:
        return f"Mail gönderme hatası: {type(e).__name__} - {e}", 500


if __name__ == "__main__":
    app.run(debug=True)
