import calendar
from datetime import datetime, time, timedelta, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.request
import urllib.error

from app.core.config import settings
from app.schemas.offer_parser import OfferParsedData, OfferParseResponse

logger = logging.getLogger(__name__)

# Month name mapping
MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# Weekdays mapping
WEEKDAY_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

KNOWN_CULTURAL_EVENTS = [
    "diwali", "deepavali", "pongal", "sankranti", "dusserah", "dasara",
    "dussehra", "navratri", "eid", "ramadan", "christmas", "new year",
    "holi", "onam", "rakhi", "raksha bandhan",
]


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _extract_category_and_items(text: str) -> Optional[str]:
    """Extract product or category keywords from text."""
    patterns = [
        r"(?:off|on|for|in|discount\s+on)\s+(?:all\s+|selected\s+|any\s+|the\s+)?([a-zA-Z\s]{3,30}?)(?:\s*(?:till|until|expires|min|minimum|above|on\s+purchases|orders|spend|valid|,|\.|$))",
        r"(?:buy\s+(?:any\s+)?\w+\s+)?([a-zA-Z\s]{3,20}?)\s+(?:discount|offer|sale)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            matched = m.group(1).strip()
            # Clean common filler words
            cleaned = re.sub(r"^(all|selected|the|our|any)\s+", "", matched, flags=re.IGNORECASE).strip()
            if cleaned and cleaned.lower() not in [
                "purchases", "orders", "bills", "products", "items", "bill", "everything", "store"
            ]:
                return cleaned.title()
            if cleaned.lower() == "everything":
                return "All Items"
    return None


def _extract_discount(text: str) -> Tuple[Optional[str], Optional[float], List[str]]:
    """Extract discount type and value from text."""
    warnings: List[str] = []
    
    # 1. Check for percentage discounts (e.g., '20% off', 'flat 15 percent discount', 'save 25%')
    pct_match = re.search(
        r"(?:flat\s+|save\s+|get\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?)\s*(?:off|discount)?",
        text,
        re.IGNORECASE,
    )
    if pct_match:
        val = float(pct_match.group(1))
        if val > 100:
            warnings.append(f"Percentage discount of {val}% exceeds 100%. Please correct.")
        elif val <= 0:
            warnings.append("Percentage discount must be greater than 0.")
        return "percentage", val, warnings

    # 2. Check for fixed discounts (e.g., '₹500 off', '500 rupees discount', 'flat 300 off', '500 rs off')
    fixed_patterns = [
        r"(?:₹|rs\.?|inr|rupees?)\s*(\d+(?:\.\d+)?)\s*(?:off|discount)?",
        r"(\d+(?:\.\d+)?)\s*(?:₹|rs\.?|inr|rupees?)\s*(?:off|discount)",
        r"(?:flat|get|save)\s*(?:₹|rs\.?|inr|rupees?)?\s*(\d+(?:\.\d+)?)\s*(?:off|discount)",
    ]
    for pattern in fixed_patterns:
        fixed_match = re.search(pattern, text, re.IGNORECASE)
        if fixed_match:
            val = float(fixed_match.group(1))
            if val <= 0:
                warnings.append("Fixed discount amount must be greater than 0.")
            return "fixed", val, warnings

    return None, None, warnings


def _extract_minimum_purchase(text: str) -> Optional[float]:
    """Extract minimum purchase or spend requirement."""
    min_patterns = [
        r"(?:min(?:imum)?\s*(?:bill|purchase|spend|order|amount)?|on\s*purchases\s*above|purchases\s*above|spend\s*(?:at\s*least)?|orders?\s*above|bill\s*above)\s*[:\-\s]*(?:₹|rs\.?|inr|rupees?)?\s*(\d+(?:\.\d+)?)",
        r"(?:above|over)\s*(?:₹|rs\.?|inr|rupees?)\s*(\d+(?:\.\d+)?)",
    ]
    for pattern in min_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


def _extract_dates(
    text: str, current_time: datetime
) -> Tuple[datetime, Optional[datetime], List[str]]:
    """Extract start and expiry dates."""
    warnings: List[str] = []
    starts_at = current_time
    expires_at: Optional[datetime] = None
    start_specified = False

    # Check for cultural / festival relative dates (e.g. till Diwali)
    for event in KNOWN_CULTURAL_EVENTS:
        if re.search(rf"\b(?:till|until|valid\s+till|before)\s+{event}\b", text, re.IGNORECASE):
            warnings.append(
                f"Expiry date for event '{event.title()}' could not be automatically resolved. Please confirm and set the expiry date."
            )
            return starts_at, None, warnings

    # Check ISO date e.g. 2026-09-30
    iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        try:
            year, month, day = int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3))
            expires_at = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
        except ValueError:
            pass

    # Check Date format e.g. 'September 30', '30th September', '30 Sep'
    if not expires_at:
        # Pattern 1: Month Day (e.g., September 30, Sep 30th)
        m_d = re.search(
            r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\b",
            text,
            re.IGNORECASE,
        )
        if m_d:
            month_str = m_d.group(1).lower()
            day = int(m_d.group(2))
            month = MONTH_MAP.get(month_str, MONTH_MAP.get(month_str[:3]))
            if month:
                year = current_time.year
                # If date in current year is already past, assume next year
                try:
                    exp_dt = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
                    if exp_dt < current_time:
                        exp_dt = datetime(year + 1, month, day, 23, 59, 59, tzinfo=timezone.utc)
                    expires_at = exp_dt
                except ValueError:
                    pass

    if not expires_at:
        # Pattern 2: Day Month (e.g., 25th September, 30 Sep)
        d_m = re.search(
            r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
            text,
            re.IGNORECASE,
        )
        if d_m:
            day = int(d_m.group(1))
            month_str = d_m.group(2).lower()
            month = MONTH_MAP.get(month_str, MONTH_MAP.get(month_str[:3]))
            if month:
                year = current_time.year
                try:
                    exp_dt = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
                    if exp_dt < current_time:
                        exp_dt = datetime(year + 1, month, day, 23, 59, 59, tzinfo=timezone.utc)
                    expires_at = exp_dt
                except ValueError:
                    pass

    # Check Day of week (e.g. till Sunday)
    if not expires_at:
        dow_match = re.search(
            r"\b(?:till|until|expires\s+on)\s+(monday|mon|tuesday|tue|tues|wednesday|wed|thursday|thu|thur|thurs|friday|fri|saturday|sat|sunday|sun)\b",
            text,
            re.IGNORECASE,
        )
        if dow_match:
            target_dow = WEEKDAY_MAP[dow_match.group(1).lower()]
            current_dow = current_time.weekday()
            days_ahead = (target_dow - current_dow) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next upcoming occurrence
            target_date = current_time.date() + timedelta(days=days_ahead)
            expires_at = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, tzinfo=timezone.utc)

    # Check relative duration (e.g. valid for 7 days)
    if not expires_at:
        rel_match = re.search(r"\b(?:valid\s+for|in|next)\s+(\d+)\s+days?\b", text, re.IGNORECASE)
        if rel_match:
            num_days = int(rel_match.group(1))
            target_dt = current_time + timedelta(days=num_days)
            expires_at = datetime(target_dt.year, target_dt.month, target_dt.day, 23, 59, 59, tzinfo=timezone.utc)

    if not start_specified:
        warnings.append("Start date was not explicitly specified and defaults to current time.")

    if expires_at is None:
        warnings.append("Expiry date could not be confidently determined. Please confirm or specify an expiry date.")
    elif expires_at <= starts_at:
        warnings.append("Expiry date must be later than start date.")

    return starts_at, expires_at, warnings


def fallback_parser(text: str, current_time: Optional[datetime] = None) -> OfferParseResponse:
    """
    Deterministic rule-based fallback parser for natural language offer descriptions.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    else:
        current_time = _ensure_utc(current_time)

    clean_text = text.strip()
    warnings: List[str] = []
    
    # 1. Extract discount
    discount_type, discount_value, disc_warnings = _extract_discount(clean_text)
    warnings.extend(disc_warnings)

    # If no discount could be extracted at all, input is likely not an offer
    if discount_type is None or discount_value is None:
        warnings.append("Could not identify a valid discount offer in the provided text.")
        return OfferParseResponse(
            original_text=clean_text,
            parsed=None,
            confidence=0.0,
            needs_confirmation=True,
            warnings=warnings,
            parser_type="fallback",
        )

    # 2. Extract minimum purchase
    minimum_purchase = _extract_minimum_purchase(clean_text)

    # 3. Extract dates
    starts_at, expires_at, date_warnings = _extract_dates(clean_text, current_time)
    warnings.extend(date_warnings)

    # 4. Extract Category / Product / Conditions
    category = _extract_category_and_items(clean_text)
    
    # 5. Formulate suggested title & description
    if discount_type == "percentage":
        disc_str = f"{int(discount_value) if discount_value.is_integer() else discount_value}% Off"
    else:
        disc_str = f"₹{int(discount_value) if discount_value.is_integer() else discount_value} Off"

    if category:
        title = f"{disc_str} on {category}"
        description = f"Flat {disc_str.lower()} applicable on {category.lower()}."
        conditions = f"Applicable to {category.lower()}"
    else:
        title = f"{disc_str} Special Offer"
        description = f"{disc_str} on eligible store purchases."
        conditions = None

    if minimum_purchase:
        description += f" Minimum purchase ₹{int(minimum_purchase) if minimum_purchase.is_integer() else minimum_purchase}."

    # 6. Calculate heuristic confidence score
    confidence = 0.5  # base for valid discount
    if category:
        confidence += 0.2
    if expires_at is not None:
        confidence += 0.2
    if minimum_purchase is not None:
        confidence += 0.1
    confidence = min(round(confidence, 2), 1.0)

    parsed_data = OfferParsedData(
        title=title,
        description=description,
        discount_type=discount_type,
        discount_value=discount_value,
        minimum_purchase=minimum_purchase,
        starts_at=starts_at,
        expires_at=expires_at,
        conditions=conditions,
    )

    return OfferParseResponse(
        original_text=clean_text,
        parsed=parsed_data,
        confidence=confidence,
        needs_confirmation=True,
        warnings=warnings,
        parser_type="fallback",
    )


def _call_ai_provider(text: str, current_time: datetime) -> Optional[OfferParseResponse]:
    """
    Attempt structured AI completion using configured external LLM provider.
    Returns None if provider is unconfigured, unreachable, or fails.
    """
    if not settings.ai_api_key or settings.ai_provider == "fallback":
        return None

    try:
        # Construct strict structured prompt
        system_prompt = (
            "You are an expert natural-language offer parser for local neighbourhood retail stores.\n"
            "Extract structured offer parameters from the shopkeeper's input text into a strict JSON object.\n"
            "Supported discount_type values: 'percentage' or 'fixed'.\n"
            "Rules:\n"
            "- Extract discount_value as a number.\n"
            "- Extract minimum_purchase as a number if mentioned, else null.\n"
            "- If expiry date is mentioned, resolve it to ISO 8601 UTC timestamp; if ambiguous (e.g. 'till Diwali'), set expires_at to null and add a warning.\n"
            "- If start date is not mentioned, suggest current time as starts_at.\n"
            "- Extract title, description, and conditions.\n"
            "- Do not invent facts.\n"
            "Return JSON matching: {title, description, discount_type, discount_value, minimum_purchase, starts_at, expires_at, conditions, warnings, confidence}"
        )
        
        user_prompt = f"Current UTC Time: {current_time.isoformat()}\nInput Text: \"{text}\""

        # Example OpenAI-compatible API call
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.ai_api_key}",
        }
        body = {
            "model": settings.ai_model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            parsed_json = json.loads(content)

            parsed_data = OfferParsedData(
                title=parsed_json.get("title"),
                description=parsed_json.get("description"),
                discount_type=parsed_json.get("discount_type"),
                discount_value=parsed_json.get("discount_value"),
                minimum_purchase=parsed_json.get("minimum_purchase"),
                starts_at=parsed_json.get("starts_at") or current_time,
                expires_at=parsed_json.get("expires_at"),
                conditions=parsed_json.get("conditions"),
            )

            warnings = parsed_json.get("warnings", [])
            if not isinstance(warnings, list):
                warnings = [str(warnings)]

            return OfferParseResponse(
                original_text=text,
                parsed=parsed_data,
                confidence=parsed_json.get("confidence", 0.9),
                needs_confirmation=True,
                warnings=warnings,
                parser_type="ai",
            )
    except Exception as e:
        logger.warning(f"AI parser provider unavailable or failed: {e.__class__.__name__}. Falling back to deterministic parser.")
        return None


def parse_offer_text(text: str, current_time: Optional[datetime] = None) -> OfferParseResponse:
    """
    Main entrypoint for parsing shopkeeper natural language offer text.
    Uses configured AI provider if available, otherwise seamlessly utilizes the deterministic fallback parser.
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    else:
        current_time = _ensure_utc(current_time)

    # 1. Attempt AI Provider if configured
    if settings.ai_api_key and settings.ai_provider != "fallback":
        ai_response = _call_ai_provider(text, current_time)
        if ai_response is not None:
            return ai_response

    # 2. Deterministic Fallback Parser
    return fallback_parser(text, current_time)
