from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)

    password_hash = Column(String(255), nullable=False)

    role = Column(String(50), default="participant", nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_disabled = Column(Boolean, default=False, nullable=False)

    marketing_consent = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submissions = relationship(
        "Submission",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    volunteer_hours = relationship(
        "VolunteerHour",
        foreign_keys="VolunteerHour.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class EmailVerificationCode(Base):
        __tablename__ = "email_verification_codes"

        id = Column(Integer, primary_key=True, index=True)
        email = Column(String(255), index=True, nullable=False)
        code = Column(String(6), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)


class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    __table_args__ = (
        CheckConstraint(
            "category IN ('studenti_fictiune', 'studenti_documentar', 'film_amator_liceeni')",
            name="ck_submissions_category"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    production_year = Column(String(20), nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    city = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=True)

    presentation = Column(Text, nullable=False)
    short_film_link = Column(Text, nullable=False)

    contact_phone = Column(String(50), nullable=False)
    contact_email = Column(String(255), nullable=False)

    coordinator_name = Column(String(255), nullable=True)
    coordinator_email = Column(String(255), nullable=True)

    other_details = Column(Text, nullable=True)

    accept_rules = Column(Boolean, default=False, nullable=False)
    accept_gdpr = Column(Boolean, default=False, nullable=False)
    accept_cookies = Column(Boolean, default=False, nullable=False)
    marketing_consent = Column(Boolean, default=False, nullable=False)

    status = Column(String(50), default="trimisa", nullable=False)
    admin_feedback = Column(Text, nullable=True)

    can_edit = Column(Boolean, default=False, nullable=False)


    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="submissions")

    team_members = relationship(
        "SubmissionTeamMember",
        back_populates="submission",
        cascade="all, delete-orphan"
    )

    material_links = relationship(
        "SubmissionMaterialLink",
        back_populates="submission",
        cascade="all, delete-orphan"
    )

class SubmissionTeamMember(Base):
    __tablename__ = "submission_team_members"

    id = Column(Integer, primary_key=True, index=True)

    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)

    name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)

    submission = relationship("Submission", back_populates="team_members")


class SubmissionMaterialLink(Base):
    __tablename__ = "submission_material_links"

    id = Column(Integer, primary_key=True, index=True)

    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)

    url = Column(Text, nullable=False)

    submission = relationship("Submission", back_populates="material_links")


class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    partner_type = Column(String(100), nullable=True)
    package = Column(String(100), nullable=True)

    logo_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdminAction(Base):
    __tablename__ = "admin_actions"

    id = Column(Integer, primary_key=True, index=True)

    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action_type = Column(String(100), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(Integer, nullable=True)

    description = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class NewsPost(Base):
    __tablename__ = "news_posts"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    category = Column(String(100), default="Anunț", nullable=False)
    cover_image_url = Column(String(500), nullable=True)

    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

class VolunteerHour(Base):
    __tablename__ = "volunteer_hours"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    activity = Column(String(100), nullable=False)
    hours = Column(Integer, nullable=False)

    status = Column(String(50), default="in_asteptare", nullable=False)
    admin_feedback = Column(Text, nullable=True)

    approved_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="volunteer_hours"
    )

    approved_by_admin = relationship(
        "User",
        foreign_keys=[approved_by_admin_id]
    )

class VolunteerProfile(Base):
    __tablename__ = "volunteer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    festival_departments = Column(Text, nullable=True)
    club_departments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class VolunteerInviteCode(Base):
    __tablename__ = "volunteer_invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)

    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class VolunteerAutoApprovalCode(Base):
    __tablename__ = "volunteer_auto_approval_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)

    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
