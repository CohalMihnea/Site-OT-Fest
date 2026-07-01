from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from email_service import send_submission_status_email

from database import get_db
from models import Submission, User
from routers.account_routes import get_current_user


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)


class SubmissionStatusUpdate(BaseModel):
    status: str
    admin_feedback: str | None = None
    can_edit: bool = False


def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Acces permis doar administratorilor."
        )

    return current_user


def serialize_user(user: User):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_admin": user.is_admin,
        "is_verified": user.is_verified,
        "is_disabled": user.is_disabled,
        "created_at": user.created_at
    }


def serialize_submission(submission: Submission):
    return {
        "id": submission.id,
        "user_id": submission.user_id,
        "user": serialize_user(submission.user) if submission.user else None,
        "title": submission.title,
        "category": submission.category,
        "production_year": submission.production_year,
        "duration_minutes": submission.duration_minutes,
        "city": submission.city,
        "marketing_consent": submission.marketing_consent,
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
        "updated_at": submission.updated_at,
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


@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    total_users = db.query(User).count()
    total_submissions = db.query(Submission).count()

    trimise = db.query(Submission).filter(Submission.status == "trimisa").count()
    in_verificare = db.query(Submission).filter(Submission.status == "in_verificare").count()
    necesita_modificari = db.query(Submission).filter(Submission.status == "necesita_modificari").count()
    acceptate = db.query(Submission).filter(Submission.status == "acceptata").count()
    respinse = db.query(Submission).filter(Submission.status == "respinsa").count()

    return {
        "total_users": total_users,
        "total_submissions": total_submissions,
        "by_status": {
            "trimisa": trimise,
            "in_verificare": in_verificare,
            "necesita_modificari": necesita_modificari,
            "acceptata": acceptate,
            "respinsa": respinse
        }
    }


@router.get("/submissions")
def get_all_submissions(
    status: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(Submission).order_by(Submission.created_at.desc())

    if status:
        query = query.filter(Submission.status == status)

    submissions = query.all()

    return {
        "submissions": [
            serialize_submission(submission)
            for submission in submissions
        ]
    }


@router.get("/submissions/{submission_id}")
def get_submission_by_id(
    submission_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Înscrierea nu a fost găsită."
        )

    return {
        "submission": serialize_submission(submission)
    }


@router.patch("/submissions/{submission_id}/status")
def update_submission_status(
    submission_id: int,
    payload: SubmissionStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    allowed_statuses = [
        "trimisa",
        "in_verificare",
        "necesita_modificari",
        "acceptata",
        "respinsa"
    ]

    if payload.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status invalid."
        )

    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Înscrierea nu a fost găsită."
        )

    old_status = submission.status

    submission.status = payload.status
    submission.admin_feedback = payload.admin_feedback

    if payload.status == "necesita_modificari":
        submission.can_edit = True
    else:
        submission.can_edit = payload.can_edit

    db.commit()
    db.refresh(submission)

    email_sent = False
    email_should_be_sent = (
        old_status != payload.status
        and bool(submission.marketing_consent)
    )

    if email_should_be_sent:
        recipient_email = submission.contact_email

        if not recipient_email and submission.user:
            recipient_email = submission.user.email

        if recipient_email:
            email_sent = send_submission_status_email(
                to_email=recipient_email,
                film_title=submission.title,
                status=submission.status,
                admin_feedback=submission.admin_feedback
            )

    return {
        "detail": "Statusul înscrierii a fost actualizat.",
        "email_sent": email_sent,
        "email_should_be_sent": email_should_be_sent,
        "submission": serialize_submission(submission)
    }

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    users = db.query(User).order_by(User.created_at.desc()).all()

    return {
        "users": [
            serialize_user(user)
            for user in users
        ]
    }


@router.patch("/users/{user_id}/disable")
def disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Utilizatorul nu a fost găsit."
        )

    if user.is_admin:
        raise HTTPException(
            status_code=400,
            detail="Nu poți dezactiva un cont de admin din panou."
        )

    user.is_disabled = True
    db.commit()

    return {
        "detail": "Contul a fost dezactivat."
    }


@router.patch("/users/{user_id}/enable")
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Utilizatorul nu a fost găsit."
        )

    user.is_disabled = False
    db.commit()

    return {
        "detail": "Contul a fost reactivat."
    }

@router.delete("/submissions/{submission_id}")
def delete_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Înscrierea nu a fost găsită."
        )

    db.delete(submission)
    db.commit()

    return {
        "detail": "Înscrierea a fost ștearsă definitiv."
    }