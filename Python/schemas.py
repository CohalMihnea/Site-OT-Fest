from enum import Enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


# -------------------------
# AUTH
# -------------------------

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=10)
    new_password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: EmailStr
    is_admin: bool


# -------------------------
# ACCOUNT
# -------------------------

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    is_admin: bool
    is_verified: bool
    is_disabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# SUBMISSION
# -------------------------

class SubmissionCategory(str, Enum):
    STUDENTI_FICTIUNE = "studenti_fictiune"
    STUDENTI_DOCUMENTAR = "studenti_documentar"
    FILM_AMATOR_LICEENI = "film_amator_liceeni"


class TeamMemberInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)


class MaterialLinkInput(BaseModel):
    url: str = Field(..., min_length=5)


class SubmissionCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: SubmissionCategory
    production_year: str = Field(..., min_length=4, max_length=20)
    duration_minutes: int = Field(..., ge=1)

    city: Optional[str] = None
    institution: Optional[str] = None

    presentation: str = Field(..., min_length=1)
    short_film_link: str = Field(..., min_length=5)

    contact_phone: str = Field(..., min_length=5, max_length=50)
    contact_email: EmailStr

    coordinator_name: Optional[str] = None
    coordinator_email: Optional[EmailStr] = None

    other_details: Optional[str] = None

    team_members: List[TeamMemberInput] = Field(default_factory=list)
    material_links: List[MaterialLinkInput] = Field(default_factory=list)

    accept_rules: bool
    accept_gdpr: bool
    accept_cookies: bool
    marketing_consent: bool = False


class SubmissionTeamMemberResponse(BaseModel):
    id: int
    name: str
    role: str

    class Config:
        from_attributes = True


class SubmissionMaterialLinkResponse(BaseModel):
    id: int
    url: str

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: int
    user_id: int

    title: str
    category: str
    production_year: str
    duration_minutes: int

    city: Optional[str] = None
    institution: Optional[str] = None

    presentation: str
    short_film_link: str

    contact_phone: str
    contact_email: EmailStr

    coordinator_name: Optional[str] = None
    coordinator_email: Optional[EmailStr] = None

    other_details: Optional[str] = None

    status: str
    admin_feedback: Optional[str] = None
    can_edit: bool

    created_at: datetime
    updated_at: Optional[datetime] = None

    team_members: List[SubmissionTeamMemberResponse] = []
    material_links: List[SubmissionMaterialLinkResponse] = []

    class Config:
        from_attributes = True


# -------------------------
# VOLUNTEERS
# -------------------------

class VolunteerEventType(str, Enum):
    CLUB = "club"
    FESTIVAL_OFF = "festival_off"


class VolunteerManualHourCreateRequest(BaseModel):
    event_type: VolunteerEventType
    task: str = Field(..., min_length=1, max_length=255)
    work_date: str = Field(..., min_length=8, max_length=20)
    hours: int = Field(..., ge=1, le=24)
    mentions: Optional[str] = None


class VolunteerHourCodeUseRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=20)


class AdminVolunteerHourCodeCreateRequest(BaseModel):
    event_type: VolunteerEventType
    task: str = Field(..., min_length=1, max_length=255)
    work_date: str = Field(..., min_length=8, max_length=20)
    hours: int = Field(..., ge=1, le=24)
    mentions: Optional[str] = None


class VolunteerHourStatusUpdateRequest(BaseModel):
    status: str
    admin_feedback: Optional[str] = None


class VolunteerCodeVerifyRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=20)


class VolunteerJoinRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=20)
    festival_departments: List[str] = Field(default_factory=list)
    club_departments: List[str] = Field(default_factory=list)


# Compatibility names used by older frontend/routes. They can remain without affecting the new flow.
class VolunteerActivity(str, Enum):
    ORGANIZARE = "organizare"
    PROMOVARE = "promovare"
    LOGISTICA = "logistica"
    SUPORT_EVENIMENT = "suport_eveniment"


class VolunteerHourCreateRequest(BaseModel):
    activity: Optional[VolunteerActivity] = None
    hours: int = Field(..., ge=1, le=24)
    auto_approval_code: Optional[str] = None


# -------------------------
# ADMIN
# -------------------------

class AdminUpdateSubmissionRequest(BaseModel):
    status: str
    admin_feedback: Optional[str] = None


class AdminSubmissionResponse(SubmissionResponse):
    user: Optional[UserResponse] = None


class ContactMessageCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    subject: Optional[str] = None
    message: str = Field(..., min_length=1)


class PartnerResponse(BaseModel):
    id: int
    name: str
    category: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
