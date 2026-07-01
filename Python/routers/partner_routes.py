from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Partner, User
from routers.account_routes import get_current_user


router = APIRouter(
    tags=["Partners"]
)


class PartnerPayload(BaseModel):
    name: str
    partner_type: str | None = None
    package: str | None = None
    logo_url: str | None = None
    website_url: str | None = None
    description: str | None = None
    display_order: int = 0
    is_active: bool = True


def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Acces permis doar administratorilor."
        )

    return current_user


def serialize_partner(partner: Partner):
    return {
        "id": partner.id,
        "name": partner.name,
        "partner_type": partner.partner_type,
        "package": partner.package,
        "logo_url": partner.logo_url,
        "website_url": partner.website_url,
        "description": partner.description,
        "display_order": partner.display_order,
        "is_active": partner.is_active,
        "created_at": partner.created_at,
        "updated_at": partner.updated_at
    }


@router.get("/api/partners")
def get_public_partners(
    db: Session = Depends(get_db)
):
    partners = (
        db.query(Partner)
        .filter(Partner.is_active == True)
        .order_by(Partner.display_order.asc(), Partner.name.asc())
        .all()
    )

    return {
        "partners": [
            serialize_partner(partner)
            for partner in partners
        ]
    }


@router.get("/api/admin/partners")
def get_admin_partners(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    partners = (
        db.query(Partner)
        .order_by(Partner.display_order.asc(), Partner.name.asc())
        .all()
    )

    return {
        "partners": [
            serialize_partner(partner)
            for partner in partners
        ]
    }


@router.post("/api/admin/partners")
def create_partner(
    payload: PartnerPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    if not payload.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Numele partenerului este obligatoriu."
        )

    existing_partner = (
        db.query(Partner)
        .filter(Partner.name == payload.name.strip())
        .first()
    )

    if existing_partner:
        raise HTTPException(
            status_code=400,
            detail="Există deja un partener cu acest nume."
        )

    partner = Partner(
        name=payload.name.strip(),
        partner_type=payload.partner_type.strip() if payload.partner_type else None,
        package=payload.package.strip() if payload.package else None,
        logo_url=payload.logo_url.strip() if payload.logo_url else None,
        website_url=payload.website_url.strip() if payload.website_url else None,
        description=payload.description.strip() if payload.description else None,
        display_order=payload.display_order,
        is_active=payload.is_active
    )

    db.add(partner)
    db.commit()
    db.refresh(partner)

    return {
        "detail": "Partenerul a fost adăugat cu succes.",
        "partner": serialize_partner(partner)
    }


@router.patch("/api/admin/partners/{partner_id}")
def update_partner(
    partner_id: int,
    payload: PartnerPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    partner = db.query(Partner).filter(Partner.id == partner_id).first()

    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Partenerul nu a fost găsit."
        )

    if not payload.name.strip():
        raise HTTPException(
            status_code=400,
            detail="Numele partenerului este obligatoriu."
        )

    partner.name = payload.name.strip()
    partner.partner_type = payload.partner_type.strip() if payload.partner_type else None
    partner.package = payload.package.strip() if payload.package else None
    partner.logo_url = payload.logo_url.strip() if payload.logo_url else None
    partner.website_url = payload.website_url.strip() if payload.website_url else None
    partner.description = payload.description.strip() if payload.description else None
    partner.display_order = payload.display_order
    partner.is_active = payload.is_active

    db.commit()
    db.refresh(partner)

    return {
        "detail": "Partenerul a fost actualizat cu succes.",
        "partner": serialize_partner(partner)
    }


@router.delete("/api/admin/partners/{partner_id}")
def delete_partner(
    partner_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    partner = db.query(Partner).filter(Partner.id == partner_id).first()

    if not partner:
        raise HTTPException(
            status_code=404,
            detail="Partenerul nu a fost găsit."
        )

    db.delete(partner)
    db.commit()

    return {
        "detail": "Partenerul a fost șters definitiv."
    }