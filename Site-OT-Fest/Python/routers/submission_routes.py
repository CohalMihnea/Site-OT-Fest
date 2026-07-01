from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Submission, SubmissionMaterialLink, SubmissionTeamMember, User
from routers.account_routes import get_current_user
from schemas import SubmissionCreateRequest


router = APIRouter(
    prefix="/api/submissions",
    tags=["Submissions"]
)


def serialize_submission(submission: Submission):
    return {
        "id": submission.id,
        "user_id": submission.user_id,
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


@router.post("")
def create_submission(
    payload: SubmissionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Emailul contului trebuie verificat înainte de înscriere."
        )

    existing_submission = (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .first()
    )

    if existing_submission:
        raise HTTPException(
            status_code=400,
            detail="Ai deja o înscriere trimisă. O poți modifica doar dacă adminul marchează înscrierea ca necesitând modificări."
        )

    if not payload.accept_rules or not payload.accept_gdpr or not payload.accept_cookies:
        raise HTTPException(
            status_code=400,
            detail="Trebuie să accepți regulamentul, politica GDPR și politica de cookies."
        )

    if len(payload.team_members) == 0:
        raise HTTPException(
            status_code=400,
            detail="Trebuie să adaugi cel puțin un membru în echipă."
        )

    submission = Submission(
        user_id=current_user.id,
        title=payload.title.strip(),
        category=payload.category.strip(),
        production_year=payload.production_year.strip(),
        duration_minutes=payload.duration_minutes,
        city=payload.city.strip() if payload.city else None,
        institution=payload.institution.strip() if payload.institution else None,
        presentation=payload.presentation.strip(),
        short_film_link=payload.short_film_link.strip(),
        contact_phone=payload.contact_phone.strip(),
        contact_email=str(payload.contact_email).strip().lower(),
        coordinator_name=payload.coordinator_name.strip() if payload.coordinator_name else None,
        coordinator_email=str(payload.coordinator_email).strip().lower() if payload.coordinator_email else None,
        other_details=payload.other_details.strip() if payload.other_details else None,
        accept_rules=payload.accept_rules,
        accept_gdpr=payload.accept_gdpr,
        accept_cookies=payload.accept_cookies,
        marketing_consent=payload.marketing_consent,
        status="trimisa",
        admin_feedback=None,
        can_edit=False
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    for member in payload.team_members:
        db.add(
            SubmissionTeamMember(
                submission_id=submission.id,
                name=member.name.strip(),
                role=member.role.strip()
            )
        )

    for link in payload.material_links:
        clean_url = link.url.strip()

        if clean_url:
            db.add(
                SubmissionMaterialLink(
                    submission_id=submission.id,
                    url=clean_url
                )
            )

    db.commit()
    db.refresh(submission)

    return {
        "detail": "Înscriere trimisă cu succes.",
        "submission": serialize_submission(submission)
    }


@router.get("/my")
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
        "submission": serialize_submission(submission)
    }


@router.put("/my")
def update_my_submission(
    payload: SubmissionCreateRequest,
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
        raise HTTPException(
            status_code=404,
            detail="Nu există o înscriere de modificat."
        )

    if submission.status != "necesita_modificari" or not submission.can_edit:
        raise HTTPException(
            status_code=403,
            detail="Înscrierea poate fi modificată doar dacă adminul solicită modificări."
        )

    if not payload.accept_rules or not payload.accept_gdpr or not payload.accept_cookies:
        raise HTTPException(
            status_code=400,
            detail="Trebuie să accepți regulamentul, politica GDPR și politica de cookies."
        )

    if len(payload.team_members) == 0:
        raise HTTPException(
            status_code=400,
            detail="Trebuie să adaugi cel puțin un membru în echipă."
        )

    submission.title = payload.title.strip()
    submission.category = payload.category.strip()
    submission.production_year = payload.production_year.strip()
    submission.duration_minutes = payload.duration_minutes
    submission.city = payload.city.strip() if payload.city else None
    submission.institution = payload.institution.strip() if payload.institution else None
    submission.presentation = payload.presentation.strip()
    submission.short_film_link = payload.short_film_link.strip()
    submission.contact_phone = payload.contact_phone.strip()
    submission.contact_email = str(payload.contact_email).strip().lower()
    submission.coordinator_name = payload.coordinator_name.strip() if payload.coordinator_name else None
    submission.coordinator_email = str(payload.coordinator_email).strip().lower() if payload.coordinator_email else None
    submission.other_details = payload.other_details.strip() if payload.other_details else None
    submission.accept_rules = payload.accept_rules
    submission.accept_gdpr = payload.accept_gdpr
    submission.accept_cookies = payload.accept_cookies
    submission.marketing_consent = payload.marketing_consent

    submission.status = "trimisa"
    submission.can_edit = False

    db.query(SubmissionTeamMember).filter(
        SubmissionTeamMember.submission_id == submission.id
    ).delete()

    db.query(SubmissionMaterialLink).filter(
        SubmissionMaterialLink.submission_id == submission.id
    ).delete()

    db.commit()

    for member in payload.team_members:
        db.add(
            SubmissionTeamMember(
                submission_id=submission.id,
                name=member.name.strip(),
                role=member.role.strip()
            )
        )

    for link in payload.material_links:
        clean_url = link.url.strip()

        if clean_url:
            db.add(
                SubmissionMaterialLink(
                    submission_id=submission.id,
                    url=clean_url
                )
            )

    db.commit()
    db.refresh(submission)

    return {
        "detail": "Înscriere modificată și retrimisă cu succes.",
        "submission": serialize_submission(submission)
    }