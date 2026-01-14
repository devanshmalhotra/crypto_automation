import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = "devanshmalhotra98@gmail.com"
SENDER_PASSWORD = "rgcsqglobazxvgt"  # Use app password if Gmail 2FA is on
RECEIVER_EMAIL = "devanshmalhotra98@gmail.com"

# Create the email
msg = MIMEMultipart()
msg["From"] = SENDER_EMAIL
msg["To"] = RECEIVER_EMAIL
msg["Subject"] = "Hello from Python"

body = "Hello!\n\nThis email was sent using a Python script.\n\nRegards,\nPython Script"
msg.attach(MIMEText(body, "plain"))

# Send the email
try:
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

    print("Email sent successfully!")

except Exception as e:
    print("Error sending email:", e)
