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

def send_submission_status_email(
            to_email: str,
            film_title: str,
            status: str,
            admin_feedback: str | None = None
    ) -> bool:
        print("=== TRIMITERE EMAIL STATUS SCURTMETRAJ ===")
        print("Către:", to_email)
        print("Film:", film_title)
        print("Status:", status)
        print("EMAIL_FROM:", EMAIL_FROM)
        print("RESEND_API_KEY există:", bool(RESEND_API_KEY))

        if not RESEND_API_KEY:
            print("ATENȚIE: RESEND_API_KEY lipsește. Emailul NU a fost trimis.")
            return False

        status_labels = {
            "trimisa": "Trimisă",
            "in_verificare": "În verificare",
            "necesita_modificari": "Necesită modificări",
            "acceptata": "Acceptată",
            "respinsa": "Respinsă"
        }

        status_label = status_labels.get(status, status)

        feedback_html = ""

        if admin_feedback:
            feedback_html = f"""
            <p><strong>Feedback din partea echipei:</strong></p>
            <p>{admin_feedback}</p>
            """

        payload = {
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": f"Status actualizat pentru scurtmetrajul tău - {FESTIVAL_NAME}",
            "html": f"""
            <h2>Status actualizat pentru scurtmetrajul tău</h2>

            <p>Bună!</p>

            <p>Statusul scurtmetrajului tău înscris la <strong>{FESTIVAL_NAME}</strong> a fost actualizat.</p>

            <p><strong>Scurtmetraj:</strong> {film_title}</p>
            <p><strong>Status nou:</strong> {status_label}</p>

            {feedback_html}

            <p>Poți vedea detaliile actualizate în contul tău de pe site.</p>

            <p>Cu drag,<br>Echipa Overthink Film Fest</p>
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
            print("EROARE TRIMITERE EMAIL STATUS SCURTMETRAJ:", error)
            return False