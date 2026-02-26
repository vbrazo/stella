from enum import StrEnum

from pydantic import BaseModel, Field


class LeadOrigin(StrEnum):
    LINKEDIN_ADS = "linkedin_ads"
    SITE = "site"
    UNKNOWN = "unknown"


class LeadCluster(StrEnum):
    STRUCTURED_EVOLUTION = "structured_evolution"
    SPECIFIC_CHALLENGE = "specific_challenge"
    FLEXIBILITY_NEEDED = "flexibility_needed"
    STRATEGIC_EVALUATION = "strategic_evaluation"


class LeadObjection(StrEnum):
    FINANCIAL_PERSONAL = "financial_personal"
    CORPORATE_DEPENDENCY = "corporate_dependency"
    SCHEDULE_LIMITATION = "schedule_limitation"
    START_SMALLER = "start_smaller"
    LACK_OF_CONVICTION = "lack_of_conviction"
    NONE = "none"


class Lead(BaseModel):
    phone: str
    name: str | None = None
    email: str | None = None
    linkedin_url: str | None = None
    origin: LeadOrigin = LeadOrigin.UNKNOWN
    kommo_id: str | None = None

    # From LinkedIn scraping
    role: str | None = None
    company: str | None = None
    seniority: str | None = None  # "manager" | "head" | "director" | "c_level"
    scraped_data: dict = Field(default_factory=dict)

    # From qualification (existing ChatGpt::QualificationService scores)
    qualification_scores: list[dict] = Field(default_factory=list)

    # From conversation
    cluster: LeadCluster | None = None
    objection: LeadObjection | None = None
    product_recommended: str | None = None

    # Financial signals
    has_financial_availability: bool | None = None
    has_live_availability: bool | None = None
    ai_interest: bool = False
    ticket_potential: str | None = None  # "high" | "medium" | "low"
