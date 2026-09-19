from flask import Flask, render_template
import socket

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
    try:
        socket.create_connection(
            ("smtp.gmail.com", 587),
            timeout=10
        )

        return "Gmail SMTP sunucusuna bağlantı başarılı!"

    except Exception as e:
        return (
            f"Gmail SMTP bağlantı hatası: "
            f"{type(e).__name__} - {e}"
        ), 500


if __name__ == "__main__":
    app.run(debug=True)
