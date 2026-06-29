import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")


HTML_DIR = PROJECT_DIR / "HTML"

if not HTML_DIR.exists():
    HTML_DIR = PROJECT_DIR / "html"

STATIC_DIR = HTML_DIR

DATABASE_URL = f"sqlite:///{BASE_DIR / 'festival.db'}"


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "schimba-aceasta-cheie-inainte-de-publicare-overthink-film-fest"
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7


RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    "Overthink Film Fest <noreply@overthink-jr.com>"
)

FESTIVAL_NAME = "Overthink Film Fest"
CONTACT_EMAIL = "staff@overthink-jr.com"
SUBMISSION_DEADLINE = "2026-08-01"