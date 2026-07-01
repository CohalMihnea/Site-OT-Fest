import requests

from config import RESEND_API_KEY, EMAIL_FROM, FESTIVAL_NAME


def send_verification_email(to_email: str, code: str) -> bool:
    print("=== TRIMITERE EMAIL VERIFICARE ===")
    print("Către:", to_email)
    print("Cod:", code)
    print("EMAIL_FROM:", EMAIL_FROM)
    print("RESEND_API_KEY există:", bool(RESEND_API_KEY))

    if not RESEND_API_KEY:
        print("ATENȚIE: RESEND_API_KEY lipsește. Emailul NU a fost trimis.")
        return False

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": f"Cod verificare cont - {FESTIVAL_NAME}",
        "html": f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Codul tău de verificare</h2>
            <p>Codul pentru verificarea contului tău Overthink Film Fest este:</p>
            <h1 style="letter-spacing: 4px;">{code}</h1>
            <p>Dacă nu ai solicitat acest cod, poți ignora acest email.</p>
        </div>
        """
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15
        )

        print("RESEND STATUS:", response.status_code)
        print("RESEND RESPONSE:", response.text)

        return response.status_code in [200, 201]

    except Exception as error:
        print("EROARE TRIMITERE EMAIL VERIFICARE:", error)
        return False


def send_password_reset_email(to_email: str, code: str) -> bool:
    print("=== TRIMITERE EMAIL RESET PAROLĂ ===")
    print("Către:", to_email)
    print("Cod:", code)
    print("EMAIL_FROM:", EMAIL_FROM)
    print("RESEND_API_KEY există:", bool(RESEND_API_KEY))

    if not RESEND_API_KEY:
        print("ATENȚIE: RESEND_API_KEY lipsește. Emailul NU a fost trimis.")
        return False

    payload = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": f"Resetare parolă - {FESTIVAL_NAME}",
        "html": f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Resetare parolă</h2>
            <p>Codul pentru resetarea parolei contului tău Overthink Film Fest este:</p>
            <h1 style="letter-spacing: 4px;">{code}</h1>
            <p>Dacă nu ai solicitat resetarea parolei, poți ignora acest email.</p>
        </div>
        """
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15
        )

        print("RESEND STATUS:", response.status_code)
        print("RESEND RESPONSE:", response.text)

        return response.status_code in [200, 201]

    except Exception as error:
        print("EROARE TRIMITERE EMAIL RESET:", error)
        return False