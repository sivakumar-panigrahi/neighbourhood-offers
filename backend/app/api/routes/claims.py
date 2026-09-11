from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_shopper
from app.db.database import get_db
from app.models.user import User
from app.schemas.claim import ClaimResponse
from app.services import claim_service

router = APIRouter(prefix="/claims", tags=["Claims"])


@router.get(
    "/my",
    response_model=List[ClaimResponse],
    summary="List all claims belonging to the authenticated shopper",
)
def list_my_claims(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter claims by status"),
    current_user: User = Depends(get_current_shopper),
    db: Session = Depends(get_db),
) -> List[ClaimResponse]:
    """
    Retrieve all claims belonging to the authenticated shopper.
    Automatically refreshes expired claims based on UTC timestamps.
    """
    claims = claim_service.get_shopper_claims(
        db,
        shopper_id=current_user.id,
        status_filter=status_filter,
    )
    return [ClaimResponse.model_validate(c) for c in claims]


@router.get(
    "/{claim_id}",
    response_model=ClaimResponse,
    summary="Get single claim details by ID (shopper owner only)",
)
def get_claim_detail(
    claim_id: int,
    current_user: User = Depends(get_current_shopper),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    """
    Retrieve a single claim by ID.
    Enforces that only the shopper who claimed the offer can access the claim.
    """
    claim = claim_service.get_claim(db, claim_id=claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found.",
        )

    if claim.shopper_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this claim.",
        )

    return ClaimResponse.model_validate(claim)
