import logging
from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_current_shopkeeper
from app.models.user import User
from app.schemas.offer_parser import OfferParseRequest, OfferParseResponse
from app.services import offer_parser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/offers", tags=["Offer Parser"])


@router.post(
    "/parse",
    response_model=OfferParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse natural-language offer text into structured parameters for review",
)
def parse_natural_language_offer(
    payload: OfferParseRequest,
    current_user: User = Depends(get_current_shopkeeper),
) -> OfferParseResponse:
    """
    Parse a shopkeeper's unstructured natural-language offer description
    into structured draft parameters for shopkeeper review and confirmation.

    NOTE: This endpoint NEVER creates a database record and NEVER activates an offer.
    """
    logger.info(f"Offer parser request received for shopkeeper ID {current_user.id}")
    return offer_parser.parse_offer_text(payload.text)
