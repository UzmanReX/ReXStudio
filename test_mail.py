import os
import smtplib
from email.mime.text import MIMEText

GMAIL_ADRESI = os.environ["rexstudiosupport@gmail.com"]
GMAIL_UYGULAMA_SIFRESI = os.environ["plxytbetznrlwlzz"]
TEST_ALICI = os.environ["galatasaray01efe@gmail.com"]

mesaj = MIMEText(
    """Merhaba!

Bu ReXStudio test mailidir.

Gmail kod gönderme sistemi çalışıyor.
""",
    "plain",
    "utf-8"
)

mesaj["Subject"] = "ReXStudio Test"
mesaj["From"] = GMAIL_ADRESI
mesaj["To"] = TEST_ALICI

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(GMAIL_ADRESI, GMAIL_UYGULAMA_SIFRESI)
    server.send_message(mesaj)

print("Mail başarıyla gönderildi!")
