import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User,
    VolunteerHour,
    VolunteerProfile,
    VolunteerInviteCode,
    VolunteerAutoApprovalCode
)
from routers.account_routes import get_current_user
from routers.admin_routes import require_admin
from schemas import (
    VolunteerHourCreateRequest,
    VolunteerHourStatusUpdateRequest,
    VolunteerCodeVerifyRequest,
    VolunteerJoinRequest
)


router = APIRouter(tags=["Volunteers"])


ALLOWED_VOLUNTEER_STATUSES = [
    "in_asteptare",
    "acceptata",
    "respinsa"
]

FESTIVAL_DEPARTMENTS = [
    "Productie",
    "Marketing",
    "Directie artistica si continut",
    "Decor"
]

CLUB_DEPARTMENTS = [
    "Productie si Marketing",
    "Creativ",
    "Actorie",
    "Tehnic"
]


def is_volunteer(user: User):
    return user.role == "voluntar" or user.is_admin


def generate_code():
    return secrets.token_hex(3).upper()


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


def serialize_profile(profile: VolunteerProfile | None):
    if not profile:
        return None

    try:
        festival_departments = json.loads(profile.festival_departments or "[]")
    except Exception:
        festival_departments = []

    try:
        club_departments = json.loads(profile.club_departments or "[]")
    except Exception:
        club_departments = []

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "festival_departments": festival_departments,
        "club_departments": club_departments,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


def get_valid_invite_code(db: Session, code: str):
    clean_code = code.strip().upper()

    invite = (
        db.query(VolunteerInviteCode)
        .filter(VolunteerInviteCode.code == clean_code)
        .first()
    )

    if not invite:
        raise HTTPException(status_code=404, detail="Codul de voluntar nu există.")

    if invite.used_at is not None:
        raise HTTPException(status_code=400, detail="Codul de voluntar a fost deja folosit.")

    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Codul de voluntar a expirat.")

    return invite


def get_valid_auto_approval_code(db: Session, code: str):
    clean_code = code.strip().upper()

    auto_code = (
        db.query(VolunteerAutoApprovalCode)
        .filter(VolunteerAutoApprovalCode.code == clean_code)
        .first()
    )

    if not auto_code:
        return None

    if auto_code.used_at is not None:
        return None

    if auto_code.expires_at < datetime.utcnow():
        return None

    return auto_code


@router.get("/api/volunteer/departments")
def get_volunteer_departments(
    current_user: User = Depends(get_current_user)
):
    return {
        "festival_departments": FESTIVAL_DEPARTMENTS,
        "club_departments": CLUB_DEPARTMENTS
    }


@router.post("/api/volunteer/code/verify")
def verify_volunteer_code(
    payload: VolunteerCodeVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_valid_invite_code(db, payload.code)

    return {
        "detail": "Cod valid. Poți completa chestionarul de voluntar.",
        "festival_departments": FESTIVAL_DEPARTMENTS,
        "club_departments": CLUB_DEPARTMENTS
    }


@router.post("/api/volunteer/join")
def join_as_volunteer(
    payload: VolunteerJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.is_admin:
        raise HTTPException(
            status_code=400,
            detail="Conturile de admin nu trebuie transformate în voluntari."
        )

    invite = get_valid_invite_code(db, payload.code)

    invalid_festival = [
        dep for dep in payload.festival_departments
        if dep not in FESTIVAL_DEPARTMENTS
    ]

    invalid_club = [
        dep for dep in payload.club_departments
        if dep not in CLUB_DEPARTMENTS
    ]

    if invalid_festival or invalid_club:
        raise HTTPException(
            status_code=400,
            detail="Ai selectat unul sau mai multe departamente invalide."
        )

    if not payload.festival_departments and not payload.club_departments:
        raise HTTPException(
            status_code=400,
            detail="Selectează cel puțin un departament."
        )

    current_user.role = "voluntar"

    profile = (
        db.query(VolunteerProfile)
        .filter(VolunteerProfile.user_id == current_user.id)
        .first()
    )

    if not profile:
        profile = VolunteerProfile(
            user_id=current_user.id
        )
        db.add(profile)

    profile.festival_departments = json.dumps(payload.festival_departments, ensure_ascii=False)
    profile.club_departments = json.dumps(payload.club_departments, ensure_ascii=False)

    invite.used_by_user_id = current_user.id
    invite.used_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)
    db.refresh(profile)

    return {
        "detail": "Contul tău a fost activat ca voluntar.",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "is_admin": current_user.is_admin
        },
        "profile": serialize_profile(profile)
    }


@router.get("/api/volunteer/me")
def get_my_volunteer_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_volunteer(current_user):
        raise HTTPException(
            status_code=403,
            detail="Această secțiune este disponibilă doar pentru voluntari."
        )

    profile = (
        db.query(VolunteerProfile)
        .filter(VolunteerProfile.user_id == current_user.id)
        .first()
    )

    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "is_admin": current_user.is_admin
        },
        "profile": serialize_profile(profile)
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
            {"value": "organizare", "label": "Organizare"},
            {"value": "promovare", "label": "Promovare"},
            {"value": "logistica", "label": "Logistică"},
            {"value": "suport_eveniment", "label": "Suport eveniment"}
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

    status = "in_asteptare"
    admin_feedback = None
    approved_by_admin_id = None
    reviewed_at = None

    if payload.auto_approval_code:
        auto_code = get_valid_auto_approval_code(db, payload.auto_approval_code)

        if not auto_code:
            raise HTTPException(
                status_code=400,
                detail="Codul de aprobare automată este invalid sau expirat."
            )

        status = "acceptata"
        admin_feedback = "Aprobat automat prin cod generat de admin."
        approved_by_admin_id = auto_code.created_by_admin_id
        reviewed_at = datetime.utcnow()
        auto_code.used_at = datetime.utcnow()

    entry = VolunteerHour(
        user_id=current_user.id,
        activity=payload.activity.value,
        hours=payload.hours,
        status=status,
        admin_feedback=admin_feedback,
        approved_by_admin_id=approved_by_admin_id,
        reviewed_at=reviewed_at
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    if status == "acceptata":
        message = "Orele de voluntariat au fost aprobate automat."
    else:
        message = "Orele de voluntariat au fost trimise spre aprobare."

    return {
        "detail": message,
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


@router.post("/api/admin/volunteer-code")
def generate_volunteer_invite_code(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    code = generate_code()

    while db.query(VolunteerInviteCode).filter(VolunteerInviteCode.code == code).first():
        code = generate_code()

    entry = VolunteerInviteCode(
        code=code,
        created_by_admin_id=admin.id,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "detail": "Cod de voluntar generat.",
        "code": entry.code,
        "expires_at": entry.expires_at
    }


@router.post("/api/admin/volunteer-auto-approval-code")
def generate_volunteer_auto_approval_code(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    code = generate_code()

    while db.query(VolunteerAutoApprovalCode).filter(VolunteerAutoApprovalCode.code == code).first():
        code = generate_code()

    entry = VolunteerAutoApprovalCode(
        code=code,
        created_by_admin_id=admin.id,
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "detail": "Cod de aprobare automată generat.",
        "code": entry.code,
        "expires_at": entry.expires_at
    }


@router.get("/api/admin/volunteers")
def get_all_volunteers(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    volunteers = (
        db.query(User)
        .filter(User.role == "voluntar")
        .order_by(User.created_at.desc())
        .all()
    )

    result = []

    for volunteer in volunteers:
        profile = (
            db.query(VolunteerProfile)
            .filter(VolunteerProfile.user_id == volunteer.id)
            .first()
        )

        hours = (
            db.query(VolunteerHour)
            .filter(VolunteerHour.user_id == volunteer.id)
            .order_by(VolunteerHour.created_at.desc())
            .all()
        )

        result.append({
            "id": volunteer.id,
            "name": volunteer.name,
            "email": volunteer.email,
            "phone": volunteer.phone,
            "role": volunteer.role,
            "profile": serialize_profile(profile),
            "hours": [serialize_volunteer_hour(entry) for entry in hours],
            "totals": {
                "accepted": sum(entry.hours for entry in hours if entry.status == "acceptata"),
                "pending": sum(entry.hours for entry in hours if entry.status == "in_asteptare"),
                "rejected": sum(entry.hours for entry in hours if entry.status == "respinsa")
            }
        })

    return {
        "volunteers": result
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