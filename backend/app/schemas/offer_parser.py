from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class OfferParseRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural-language offer text from shopkeeper",
    )


class OfferParsedData(BaseModel):
    title: Optional[str] = Field(None, description="Suggested offer title")
    description: Optional[str] = Field(None, description="Suggested offer description")
    discount_type: Optional[Literal["percentage", "fixed"]] = Field(
        None,
        description="Parsed discount type: percentage or fixed",
    )
    discount_value: Optional[float] = Field(
        None,
        description="Parsed discount value (percentage or fixed amount)",
    )
    minimum_purchase: Optional[float] = Field(
        None,
        description="Minimum purchase amount required, if any",
    )
    starts_at: Optional[datetime] = Field(
        None,
        description="Suggested offer start timestamp (UTC)",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Suggested offer expiry timestamp (UTC)",
    )
    conditions: Optional[str] = Field(
        None,
        description="Identified category, item, or conditional rules",
    )

    model_config = ConfigDict(from_attributes=True)


class OfferParseResponse(BaseModel):
    original_text: str = Field(..., description="Original input text entered by shopkeeper")
    parsed: Optional[OfferParsedData] = Field(
        None,
        description="Extracted and structured offer fields",
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Heuristic parsing confidence score between 0.0 and 1.0",
    )
    needs_confirmation: bool = Field(
        True,
        description="Whether shopkeeper review/confirmation is required before offer creation",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of warnings, ambiguities, or validation notices",
    )
    parser_type: Literal["ai", "fallback"] = Field(
        ...,
        description="Type of parser that processed the request ('ai' or 'fallback')",
    )

    model_config = ConfigDict(from_attributes=True)
