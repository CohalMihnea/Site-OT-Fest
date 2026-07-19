import json
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User,
    VolunteerProfile,
    VolunteerInviteCode,
    VolunteerHourEntry,
    VolunteerHourCode,
)
from routers.account_routes import get_current_user
from routers.admin_routes import require_admin
from schemas import (
    AdminVolunteerHourCodeCreateRequest,
    VolunteerCodeVerifyRequest,
    VolunteerHourCodeUseRequest,
    VolunteerHourStatusUpdateRequest,
    VolunteerJoinRequest,
    VolunteerManualHourCreateRequest,
)


router = APIRouter(tags=["Volunteers"])


ALLOWED_VOLUNTEER_STATUSES = [
    "in_asteptare",
    "acceptata",
    "respinsa",
]

FESTIVAL_DEPARTMENTS = [
    "Productie",
    "Marketing",
    "Directie artistica si continut",
    "Decor",
]

CLUB_DEPARTMENTS = [
    "Productie si Marketing",
    "Creativ",
    "Actorie",
    "Tehnic",
]


def is_volunteer(user: User):
    return user.role == "voluntar" or user.is_admin


def generate_code():
    return secrets.token_hex(3).upper()


def event_label(event_type: str):
    labels = {
        "club": "Club",
        "festival_off": "Festivalul OFF",
    }
    return labels.get(event_type, event_type or "-")


def status_label(status: str):
    labels = {
        "in_asteptare": "În așteptare",
        "acceptata": "Acceptată",
        "respinsa": "Respinsă",
    }
    return labels.get(status, status or "-")


def parse_departments(raw_value: str | None):
    try:
        value = json.loads(raw_value or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def serialize_profile(profile: VolunteerProfile | None):
    if not profile:
        return None

    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "festival_departments": parse_departments(profile.festival_departments),
        "club_departments": parse_departments(profile.club_departments),
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def serialize_volunteer_hour(entry: VolunteerHourEntry):
    return {
        "id": entry.id,
        "user_id": entry.user_id,
        "user": {
            "id": entry.user.id,
            "name": entry.user.name,
            "email": entry.user.email,
            "phone": entry.user.phone,
            "role": entry.user.role,
        } if entry.user else None,
        "event_type": entry.event_type,
        "event_label": event_label(entry.event_type),
        "task": entry.task,
        "work_date": entry.work_date,
        "hours": entry.hours,
        "mentions": entry.mentions,
        "status": entry.status,
        "status_label": status_label(entry.status),
        "admin_feedback": entry.admin_feedback,
        "approval_type": entry.approval_type,
        "used_code": entry.used_code,
        "approved_by_admin_id": entry.approved_by_admin_id,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "reviewed_at": entry.reviewed_at,
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


def get_valid_hour_code(db: Session, code: str):
    clean_code = code.strip().upper()

    hour_code = (
        db.query(VolunteerHourCode)
        .filter(VolunteerHourCode.code == clean_code)
        .first()
    )

    if not hour_code:
        raise HTTPException(status_code=404, detail="Codul pentru ore nu există.")

    if hour_code.used_at is not None:
        raise HTTPException(status_code=400, detail="Codul pentru ore a fost deja folosit.")

    if hour_code.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Codul pentru ore a expirat.")

    return hour_code


def get_volunteer_profile_or_404(db: Session, user: User):
    profile = (
        db.query(VolunteerProfile)
        .filter(VolunteerProfile.user_id == user.id)
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Contul de voluntar nu are departamente completate."
        )

    return profile


def allowed_tasks_for_user(profile: VolunteerProfile, event_type: str):
    if event_type == "festival_off":
        return parse_departments(profile.festival_departments)

    if event_type == "club":
        return parse_departments(profile.club_departments)

    return []


def validate_task_for_manual_entry(db: Session, user: User, event_type: str, task: str):
    if user.is_admin:
        valid_tasks = FESTIVAL_DEPARTMENTS if event_type == "festival_off" else CLUB_DEPARTMENTS
    else:
        profile = get_volunteer_profile_or_404(db, user)
        valid_tasks = allowed_tasks_for_user(profile, event_type)

    if task not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail="Taskul ales nu aparține departamentelor tale pentru evenimentul selectat."
        )


def totals_from_entries(entries):
    return {
        "accepted": sum(entry.hours for entry in entries if entry.status == "acceptata"),
        "pending": sum(entry.hours for entry in entries if entry.status == "in_asteptare"),
        "rejected": sum(entry.hours for entry in entries if entry.status == "respinsa"),
    }


@router.get("/api/volunteer/departments")
def get_volunteer_departments(
    current_user: User = Depends(get_current_user)
):
    return {
        "events": [
            {"value": "club", "label": "Club"},
            {"value": "festival_off", "label": "Festivalul OFF"},
        ],
        "festival_departments": FESTIVAL_DEPARTMENTS,
        "club_departments": CLUB_DEPARTMENTS,
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
        "club_departments": CLUB_DEPARTMENTS,
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
        profile = VolunteerProfile(user_id=current_user.id)
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
            "is_admin": current_user.is_admin,
        },
        "profile": serialize_profile(profile),
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

    profile_data = serialize_profile(profile)

    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "is_admin": current_user.is_admin,
        },
        "profile": profile_data,
        "tasks": {
            "festival_off": profile_data["festival_departments"] if profile_data else FESTIVAL_DEPARTMENTS,
            "club": profile_data["club_departments"] if profile_data else CLUB_DEPARTMENTS,
        },
        "events": [
            {"value": "club", "label": "Club"},
            {"value": "festival_off", "label": "Festivalul OFF"},
        ],
    }


@router.post("/api/volunteer/hours/manual")
def create_manual_volunteer_hours(
    payload: VolunteerManualHourCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_volunteer(current_user):
        raise HTTPException(
            status_code=403,
            detail="Doar conturile de voluntar pot introduce ore de voluntariat."
        )

    validate_task_for_manual_entry(
        db=db,
        user=current_user,
        event_type=payload.event_type.value,
        task=payload.task,
    )

    entry = VolunteerHourEntry(
        user_id=current_user.id,
        event_type=payload.event_type.value,
        task=payload.task,
        work_date=payload.work_date,
        hours=payload.hours,
        mentions=payload.mentions,
        status="in_asteptare",
        admin_feedback=None,
        approval_type="manual",
        used_code=None,
        approved_by_admin_id=None,
        reviewed_at=None,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "detail": "Orele au fost trimise spre aprobare.",
        "entry": serialize_volunteer_hour(entry),
    }


@router.post("/api/volunteer/hours/code")
def create_volunteer_hours_with_code(
    payload: VolunteerHourCodeUseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not is_volunteer(current_user):
        raise HTTPException(
            status_code=403,
            detail="Doar conturile de voluntar pot introduce ore de voluntariat."
        )

    hour_code = get_valid_hour_code(db, payload.code)

    entry = VolunteerHourEntry(
        user_id=current_user.id,
        event_type=hour_code.event_type,
        task=hour_code.task,
        work_date=hour_code.work_date,
        hours=hour_code.hours,
        mentions=hour_code.mentions,
        status="acceptata",
        admin_feedback="Aprobat automat prin cod generat de admin.",
        approval_type="cod",
        used_code=hour_code.code,
        created_by_code_id=hour_code.id,
        approved_by_admin_id=hour_code.created_by_admin_id,
        reviewed_at=datetime.utcnow(),
    )

    db.add(entry)
    db.flush()

    hour_code.used_by_user_id = current_user.id
    hour_code.created_hour_entry_id = entry.id
    hour_code.used_at = datetime.utcnow()

    db.commit()
    db.refresh(entry)

    return {
        "detail": "Orele au fost adăugate și aprobate automat.",
        "entry": serialize_volunteer_hour(entry),
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
        db.query(VolunteerHourEntry)
        .filter(VolunteerHourEntry.user_id == current_user.id)
        .order_by(VolunteerHourEntry.created_at.desc())
        .all()
    )

    return {
        "entries": [serialize_volunteer_hour(entry) for entry in entries],
        "totals": totals_from_entries(entries),
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
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "detail": "Cod de voluntar generat.",
        "code": entry.code,
        "expires_at": entry.expires_at,
    }


@router.post("/api/admin/volunteer-hour-code")
def generate_volunteer_hour_code(
    payload: AdminVolunteerHourCodeCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    valid_tasks = FESTIVAL_DEPARTMENTS if payload.event_type.value == "festival_off" else CLUB_DEPARTMENTS

    if payload.task not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail="Task invalid pentru evenimentul selectat."
        )

    code = generate_code()

    while db.query(VolunteerHourCode).filter(VolunteerHourCode.code == code).first():
        code = generate_code()

    entry = VolunteerHourCode(
        code=code,
        event_type=payload.event_type.value,
        task=payload.task,
        work_date=payload.work_date,
        hours=payload.hours,
        mentions=payload.mentions,
        created_by_admin_id=admin.id,
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "detail": "Cod de ore generat.",
        "code": entry.code,
        "expires_at": entry.expires_at,
        "event_type": entry.event_type,
        "event_label": event_label(entry.event_type),
        "task": entry.task,
        "work_date": entry.work_date,
        "hours": entry.hours,
        "mentions": entry.mentions,
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

        entries = (
            db.query(VolunteerHourEntry)
            .filter(VolunteerHourEntry.user_id == volunteer.id)
            .order_by(VolunteerHourEntry.created_at.desc())
            .all()
        )

        result.append({
            "id": volunteer.id,
            "name": volunteer.name,
            "email": volunteer.email,
            "phone": volunteer.phone,
            "role": volunteer.role,
            "profile": serialize_profile(profile),
            "hours": [serialize_volunteer_hour(entry) for entry in entries],
            "totals": totals_from_entries(entries),
        })

    return {
        "volunteers": result,
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
            "is_admin": user.is_admin,
        },
    }


@router.get("/api/admin/volunteer-hours")
def get_all_volunteer_hours(
    status: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    query = db.query(VolunteerHourEntry).order_by(VolunteerHourEntry.created_at.desc())

    if status:
        query = query.filter(VolunteerHourEntry.status == status)

    entries = query.all()

    return {
        "entries": [serialize_volunteer_hour(entry) for entry in entries],
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

    entry = db.query(VolunteerHourEntry).filter(VolunteerHourEntry.id == entry_id).first()

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
        "entry": serialize_volunteer_hour(entry),
    }
