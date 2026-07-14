from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, VolunteerHour
from routers.account_routes import get_current_user
from routers.admin_routes import require_admin
from schemas import VolunteerHourCreateRequest, VolunteerHourStatusUpdateRequest


router = APIRouter(
    tags=["Volunteers"]
)


ALLOWED_VOLUNTEER_STATUSES = [
    "in_asteptare",
    "acceptata",
    "respinsa"
]


def is_volunteer(user: User):
    return user.role == "voluntar" or user.is_admin


def activity_label(activity: str):
    labels = {
        "organizare": "Organizare",
        "promovare": "Promovare",
        "logistica": "Logistică",
        "suport_eveniment": "Suport eveniment"
    }

    return labels.get(activity, activity)


def serialize_volunteer_hour(entry: VolunteerHour):
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "user": {
            "id": entry.user.id,
            "name": entry.user.name,
            "email": entry.user.email,
            "phone": entry.user.phone,
            "role": entry.user.role
        } if entry.user else None,
        "activity": entry.activity,
        "activity_label": activity_label(entry.activity),
        "hours": entry.hours,
        "status": entry.status,
        "admin_feedback": entry.admin_feedback,
        "approved_by_admin_id": entry.approved_by_admin_id,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "reviewed_at": entry.reviewed_at
    }


@router.get("/api/volunteer/activities")
def get_volunteer_activities(
    current_user: User = Depends(get_current_user)
):
    if not is_volunteer(current_user):
        raise HTTPException(
            status_code=403,
            detail="Această secțiune este disponibilă doar pentru voluntari."
        )

    return {
        "activities": [
            {
                "value": "organizare",
                "label": "Organizare"
            },
            {
                "value": "promovare",
                "label": "Promovare"
            },
            {
                "value": "logistica",
                "label": "Logistică"
            },
            {
                "value": "suport_eveniment",
                "label": "Suport eveniment"
            }
        ]
    }


@router.post("/api/volunteer/hours")
def create_volunteer_hours(
    payload: VolunteerHourCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_volunteer(current_user):
        raise HTTPException(
            status_code=403,
            detail="Doar conturile de voluntar pot introduce ore de voluntariat."
        )

    entry = VolunteerHour(
        user_id=current_user.id,
        activity=payload.activity.value,
        hours=payload.hours,
        status="in_asteptare",
        admin_feedback=None,
        approved_by_admin_id=None
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "detail": "Orele de voluntariat au fost trimise spre aprobare.",
        "entry": serialize_volunteer_hour(entry)
    }


@router.get("/api/volunteer/hours/my")
def get_my_volunteer_hours(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_volunteer(current_user):
        raise HTTPException(
            status_code=403,
            detail="Această secțiune este disponibilă doar pentru voluntari."
        )

    entries = (
        db.query(VolunteerHour)
        .filter(VolunteerHour.user_id == current_user.id)
        .order_by(VolunteerHour.created_at.desc())
        .all()
    )

    accepted_total = sum(entry.hours for entry in entries if entry.status == "acceptata")
    pending_total = sum(entry.hours for entry in entries if entry.status == "in_asteptare")
    rejected_total = sum(entry.hours for entry in entries if entry.status == "respinsa")

    return {
        "entries": [serialize_volunteer_hour(entry) for entry in entries],
        "totals": {
            "accepted": accepted_total,
            "pending": pending_total,
            "rejected": rejected_total
        }
    }


@router.patch("/api/admin/users/{user_id}/make-volunteer")
def make_user_volunteer(
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
            detail="Un cont de admin nu trebuie transformat în voluntar."
        )

    user.role = "voluntar"

    db.commit()
    db.refresh(user)

    return {
        "detail": "Contul a fost activat ca voluntar.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_admin": user.is_admin
        }
    }


@router.patch("/api/admin/users/{user_id}/remove-volunteer")
def remove_user_volunteer(
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

    if user.role != "voluntar":
        raise HTTPException(
            status_code=400,
            detail="Acest cont nu este voluntar."
        )

    user.role = "participant"

    db.commit()
    db.refresh(user)

    return {
        "detail": "Rolul de voluntar a fost eliminat.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_admin": user.is_admin
        }
    }


@router.get("/api/admin/volunteer-hours")
def get_all_volunteer_hours(
    status: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(VolunteerHour).order_by(VolunteerHour.created_at.desc())

    if status:
        query = query.filter(VolunteerHour.status == status)

    entries = query.all()

    return {
        "entries": [serialize_volunteer_hour(entry) for entry in entries]
    }


@router.patch("/api/admin/volunteer-hours/{entry_id}/status")
def update_volunteer_hour_status(
    entry_id: int,
    payload: VolunteerHourStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if payload.status not in ALLOWED_VOLUNTEER_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Status invalid."
        )

    entry = db.query(VolunteerHour).filter(VolunteerHour.id == entry_id).first()

    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Înregistrarea de voluntariat nu a fost găsită."
        )

    entry.status = payload.status
    entry.admin_feedback = payload.admin_feedback
    entry.approved_by_admin_id = admin.id
    entry.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(entry)

    return {
        "detail": "Statusul orelor de voluntariat a fost actualizat.",
        "entry": serialize_volunteer_hour(entry)
    }