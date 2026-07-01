from datetime import datetime
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import NewsPost, User
from routers.admin_routes import require_admin


router = APIRouter(
    prefix="/api",
    tags=["News"]
)


class NewsPostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    summary: Optional[str] = None
    content: str = Field(..., min_length=1)
    category: str = Field("Anunț", max_length=100)
    cover_image_url: Optional[str] = None
    is_published: bool = False
    is_featured: bool = False


class NewsPostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    summary: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, max_length=100)
    cover_image_url: Optional[str] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None


def make_slug(text: str) -> str:
    replacements = {
        "ă": "a",
        "â": "a",
        "î": "i",
        "ș": "s",
        "ş": "s",
        "ț": "t",
        "ţ": "t",
        "Ă": "a",
        "Â": "a",
        "Î": "i",
        "Ș": "s",
        "Ş": "s",
        "Ț": "t",
        "Ţ": "t",
    }

    clean_text = text.strip().lower()

    for original, replacement in replacements.items():
        clean_text = clean_text.replace(original, replacement)

    clean_text = re.sub(r"[^a-z0-9]+", "-", clean_text)
    clean_text = clean_text.strip("-")

    return clean_text or "noutate"


def generate_unique_slug(db: Session, title: str, current_news_id: Optional[int] = None) -> str:
    base_slug = make_slug(title)
    slug = base_slug
    counter = 2

    while True:
        query = db.query(NewsPost).filter(NewsPost.slug == slug)

        if current_news_id is not None:
            query = query.filter(NewsPost.id != current_news_id)

        existing = query.first()

        if not existing:
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1


def serialize_news_post(news_post: NewsPost):
    return {
        "id": news_post.id,
        "title": news_post.title,
        "slug": news_post.slug,
        "summary": news_post.summary,
        "content": news_post.content,
        "category": news_post.category,
        "cover_image_url": news_post.cover_image_url,
        "is_published": news_post.is_published,
        "is_featured": news_post.is_featured,
        "created_by_user_id": news_post.created_by_user_id,
        "created_at": news_post.created_at,
        "updated_at": news_post.updated_at,
        "published_at": news_post.published_at,
    }


@router.get("/news")
def get_public_news(
    category: Optional[str] = Query(default=None),
    featured: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db)
):
    query = (
        db.query(NewsPost)
        .filter(NewsPost.is_published == True)
    )

    if category and category.lower() != "toate":
        query = query.filter(NewsPost.category == category)

    if featured is not None:
        query = query.filter(NewsPost.is_featured == featured)

    news_posts = (
        query
        .order_by(NewsPost.is_featured.desc(), NewsPost.published_at.desc(), NewsPost.created_at.desc())
        .all()
    )

    return {
        "news": [serialize_news_post(news_post) for news_post in news_posts]
    }


@router.get("/news/{slug}")
def get_public_news_post(
    slug: str,
    db: Session = Depends(get_db)
):
    news_post = (
        db.query(NewsPost)
        .filter(NewsPost.slug == slug, NewsPost.is_published == True)
        .first()
    )

    if not news_post:
        raise HTTPException(
            status_code=404,
            detail="Noutatea nu a fost găsită."
        )

    return {
        "news_post": serialize_news_post(news_post)
    }


@router.get("/admin/news")
def get_admin_news(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    news_posts = (
        db.query(NewsPost)
        .order_by(NewsPost.created_at.desc())
        .all()
    )

    return {
        "news": [serialize_news_post(news_post) for news_post in news_posts]
    }


@router.post("/admin/news")
def create_news_post(
    payload: NewsPostCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    slug = generate_unique_slug(db, payload.title)
    now = datetime.utcnow()

    if payload.is_featured:
        db.query(NewsPost).update({NewsPost.is_featured: False})

    news_post = NewsPost(
        title=payload.title.strip(),
        slug=slug,
        summary=payload.summary.strip() if payload.summary else None,
        content=payload.content.strip(),
        category=payload.category.strip() if payload.category else "Anunț",
        cover_image_url=payload.cover_image_url.strip() if payload.cover_image_url else None,
        is_published=payload.is_published,
        is_featured=payload.is_featured,
        created_by_user_id=admin.id,
        published_at=now if payload.is_published else None,
    )

    db.add(news_post)
    db.commit()
    db.refresh(news_post)

    return {
        "detail": "Noutatea a fost creată.",
        "news_post": serialize_news_post(news_post)
    }


@router.patch("/admin/news/{news_id}")
def update_news_post(
    news_id: int,
    payload: NewsPostUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    news_post = db.query(NewsPost).filter(NewsPost.id == news_id).first()

    if not news_post:
        raise HTTPException(
            status_code=404,
            detail="Noutatea nu a fost găsită."
        )

    was_published = news_post.is_published

    if payload.title is not None:
        news_post.title = payload.title.strip()
        news_post.slug = generate_unique_slug(db, news_post.title, current_news_id=news_post.id)

    if payload.summary is not None:
        news_post.summary = payload.summary.strip() if payload.summary else None

    if payload.content is not None:
        news_post.content = payload.content.strip()

    if payload.category is not None:
        news_post.category = payload.category.strip() if payload.category else "Anunț"

    if payload.cover_image_url is not None:
        news_post.cover_image_url = payload.cover_image_url.strip() if payload.cover_image_url else None

    if payload.is_published is not None:
        news_post.is_published = payload.is_published

        if payload.is_published and not was_published:
            news_post.published_at = datetime.utcnow()

        if not payload.is_published:
            news_post.published_at = None

    if payload.is_featured is not None:
        if payload.is_featured:
            db.query(NewsPost).filter(NewsPost.id != news_post.id).update({NewsPost.is_featured: False})

        news_post.is_featured = payload.is_featured

    db.commit()
    db.refresh(news_post)

    return {
        "detail": "Noutatea a fost actualizată.",
        "news_post": serialize_news_post(news_post)
    }


@router.delete("/admin/news/{news_id}")
def delete_news_post(
    news_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    news_post = db.query(NewsPost).filter(NewsPost.id == news_id).first()

    if not news_post:
        raise HTTPException(
            status_code=404,
            detail="Noutatea nu a fost găsită."
        )

    db.delete(news_post)
    db.commit()

    return {
        "detail": "Noutatea a fost ștearsă."
    }
