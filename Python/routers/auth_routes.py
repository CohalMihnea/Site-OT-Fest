from datetime import datetime, timedelta
import random

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from auth import create_access_token, hash_password, verify_password
from database import get_db
from email_service import send_password_reset_email, send_verification_email
from models import EmailVerificationCode, PasswordResetCode, User


router = APIRouter(
    prefix="/api",
    tags=["Auth"]
)


def generate_code() -> str:
    return str(random.randint(100000, 999999))


def normalize_email(email: str) -> str:
    return email.strip().lower()


def save_email_verification_code(
    db: Session,
    email: str,
    code: str
):
    normalized_email = normalize_email(email)

    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == normalized_email
    ).delete()

    new_code = EmailVerificationCode(
        email=normalized_email,
        code=code,
        created_at=datetime.utcnow()
    )

    db.add(new_code)
    db.commit()

    return new_code


def get_last_email_verification_code(
    db: Session,
    email: str
):
    normalized_email = normalize_email(email)

    return (
        db.query(EmailVerificationCode)
        .filter(EmailVerificationCode.email == normalized_email)
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )


@router.post("/register")
def register(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form("participant"),
    sex: str = Form(""),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(email)

    if password != confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Parolele nu coincid."
        )

    existing_user = db.query(User).filter(User.email == normalized_email).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Există deja un cont cu această adresă de email."
        )

    user = User(
        name=name.strip(),
        email=normalized_email,
        phone=phone.strip(),
        password_hash=hash_password(password),
        role=role.strip() or "participant",
        is_admin=False,
        is_verified=False,
    )

    if hasattr(user, "sex"):
        user.sex = sex.strip()

    db.add(user)
    db.commit()
    db.refresh(user)

    verification_code = generate_code()

    save_email_verification_code(
        db=db,
        email=normalized_email,
        code=verification_code
    )

    email_sent = send_verification_email(
        to_email=normalized_email,
        code=verification_code
    )

    if not email_sent:
        return {
            "detail": "Contul a fost creat, dar emailul de verificare nu a putut fi trimis. Poți cere retrimiterea codului din pagina de autentificare."
        }

    return {
        "detail": "Cont creat cu succes. Am trimis codul de verificare pe email."
    }


@router.post("/resend-verification")
def resend_verification_code(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(email)

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Nu există niciun cont cu această adresă de email."
        )

    if user.is_verified:
        return {
            "detail": "Acest cont este deja verificat. Te poți autentifica."
        }

    cooldown_seconds = 30
    now = datetime.utcnow()

    last_code = get_last_email_verification_code(
        db=db,
        email=normalized_email
    )

    if last_code and last_code.created_at:
        elapsed_seconds = (now - last_code.created_at).total_seconds()

        if elapsed_seconds < cooldown_seconds:
            remaining_seconds = int(cooldown_seconds - elapsed_seconds)

            raise HTTPException(
                status_code=429,
                detail=f"Poți cere un nou cod peste {remaining_seconds} secunde."
            )

    verification_code = generate_code()

    save_email_verification_code(
        db=db,
        email=normalized_email,
        code=verification_code
    )

    print("COD NOU GENERAT PENTRU RETRIMITERE:", normalized_email, verification_code)

    email_sent = send_verification_email(
        to_email=normalized_email,
        code=verification_code
    )

    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Codul a fost generat și salvat, dar emailul nu a putut fi trimis. Verifică setările Resend."
        )

    return {
        "detail": "Un nou cod de verificare a fost trimis pe email."
    }


@router.post("/verify")
def verify_email(
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(email)
    clean_code = code.strip()

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Contul nu a fost găsit."
        )

    if user.is_verified:
        return {
            "detail": "Contul este deja verificat."
        }

    verification_code = (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == normalized_email,
            EmailVerificationCode.code == clean_code
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .first()
    )

    if not verification_code:
        raise HTTPException(
            status_code=400,
            detail="Codul de verificare este incorect."
        )

    user.is_verified = True

    db.query(EmailVerificationCode).filter(
        EmailVerificationCode.email == normalized_email
    ).delete()

    db.commit()

    return {
        "detail": "Email verificat cu succes. Te poți autentifica."
    }


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(email)

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Email sau parolă incorectă."
        )

    if user.is_disabled:
        raise HTTPException(
            status_code=403,
            detail="Acest cont a fost dezactivat."
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Email sau parolă incorectă."
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Emailul nu este verificat. Verifică emailul înainte de autentificare."
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin
        }
    )

    return {
        "detail": "Autentificare reușită.",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "is_admin": user.is_admin
    }


@router.post("/forgot-password")
def forgot_password(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(email)

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Nu există niciun cont cu această adresă de email."
        )

    reset_code = generate_code()
    now = datetime.utcnow()

    db.query(PasswordResetCode).filter(
        PasswordResetCode.email == normalized_email
    ).delete(synchronize_session=False)

    new_code = PasswordResetCode(
        email=normalized_email,
        code=reset_code,
        created_at=now,
        expires_at=now + timedelta(minutes=15)
    )

    db.add(new_code)
    db.commit()

    email_sent = send_password_reset_email(
        to_email=normalized_email,
        code=reset_code
    )

    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Codul a fost generat, dar emailul nu a putut fi trimis."
        )

    return {
        "detail": "Codul de resetare a fost trimis pe email."
    }

@router.post("/reset-password")
def reset_password(
    email: str = Form(...),
    code: str = Form(...),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    normalized_email = normalize_email(email)

    if new_password != confirm_new_password:
        raise HTTPException(
            status_code=400,
            detail="Parolele nu coincid."
        )

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Contul nu a fost găsit."
        )

    reset_code = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.email == normalized_email,
            PasswordResetCode.code == code.strip()
        )
        .order_by(PasswordResetCode.created_at.desc())
        .first()
    )

    if not reset_code:
        raise HTTPException(
            status_code=400,
            detail="Codul de resetare este incorect."
        )

    user.password_hash = hash_password(new_password)

    db.query(PasswordResetCode).filter(
        PasswordResetCode.email == normalized_email
    ).delete()

    db.commit()

    return {
        "detail": "Parola a fost resetată cu succes. Te poți autentifica."
    }