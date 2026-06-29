from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from auth import decode_access_token
from database import get_db
from models import User, Submission


router = APIRouter(
    prefix="/api/account",
    tags=["Account"]
)


def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Token lipsă. Te rugăm să te autentifici."
        )

    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Format token invalid."
        )

    token = parts[1]
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token invalid sau expirat."
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Token invalid."
        )

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Utilizatorul nu a fost găsit."
        )

    if user.is_disabled:
        raise HTTPException(
            status_code=403,
            detail="Contul este dezactivat."
        )

    return user


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "is_verified": current_user.is_verified,
        "is_disabled": current_user.is_disabled,
        "created_at": current_user.created_at
    }


@router.get("/my-submission")
def get_my_submission(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
        .first()
    )

    if not submission:
        return {
            "has_submission": False,
            "submission": None
        }

    return {
        "has_submission": True,
        "submission": {
            "id": submission.id,
            "title": submission.title,
            "category": submission.category,
            "production_year": submission.production_year,
            "duration_minutes": submission.duration_minutes,
            "city": submission.city,
            "institution": submission.institution,
            "presentation": submission.presentation,
            "short_film_link": submission.short_film_link,
            "contact_phone": submission.contact_phone,
            "contact_email": submission.contact_email,
            "coordinator_name": submission.coordinator_name,
            "coordinator_email": submission.coordinator_email,
            "other_details": submission.other_details,
            "status": submission.status,
            "admin_feedback": submission.admin_feedback,
            "can_edit": submission.can_edit,
            "created_at": submission.created_at,
            "team_members": [
                {
                    "id": member.id,
                    "name": member.name,
                    "role": member.role
                }
                for member in submission.team_members
            ],
            "material_links": [
                {
                    "id": link.id,
                    "url": link.url
                }
                for link in submission.material_links
            ]
        }
    }