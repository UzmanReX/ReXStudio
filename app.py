from flask import Flask, render_template

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

if __name__ == "__main__":
    app.run(debug=True)