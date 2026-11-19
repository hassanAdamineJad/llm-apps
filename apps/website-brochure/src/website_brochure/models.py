from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class BrochureCategory(StrEnum):
    BUSINESS = "business_overview"
    SPOTLIGHT = "product_service_spotlight"
    EVENT = "event_program_overview"

    @property
    def label(self) -> str:
        return {
            self.BUSINESS: "Business Overview",
            self.SPOTLIGHT: "Product or Service Spotlight",
            self.EVENT: "Event or Program Overview",
        }[self]


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    website_url: HttpUrl
    category: BrochureCategory


class BrochureSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heading: str = Field(min_length=2, max_length=100)
    body: str = Field(min_length=20, max_length=1_200)


class Brochure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=4, max_length=140)
    introduction: str = Field(min_length=20, max_length=900)
    sections: list[BrochureSection] = Field(min_length=2, max_length=5)
    # Nullable but required keeps the JSON schema compatible with strict-output APIs.
    call_to_action: str | None = Field(max_length=240)


class GeneratedContent(BaseModel):
    """The one structured-output contract used by every LLM provider."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "insufficient"]
    factual_summary: str = Field(min_length=20, max_length=1_000)
    brochure: Brochure | None
    feedback: str | None = Field(max_length=500)

    @model_validator(mode="after")
    def validate_status_fields(self) -> "GeneratedContent":
        if self.status == "ready" and self.brochure is None:
            raise ValueError("ready output requires a brochure")
        if self.status == "insufficient" and (
            self.brochure is not None or not self.feedback
        ):
            raise ValueError("insufficient output requires feedback and no brochure")
        return self


class GenerateResponse(GeneratedContent):
    source_url: HttpUrl
    page_title: str

