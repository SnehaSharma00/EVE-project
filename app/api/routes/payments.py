from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Process simulated payment",
    description="Processes a mock payment, updating booking status to CONFIRMED or FAILED.",
)
def create_payment(
    payment_in: PaymentCreate,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        description="Unique idempotency key for safe payment retries",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaymentResponse:
    payment = payment_service.process_payment(
        db=db,
        user=current_user,
        payment_in=payment_in,
        idempotency_key=idempotency_key,
    )
    return PaymentResponse.model_validate(payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payment details",
    description="Fetches full details of a payment by its internal ID.",
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaymentResponse:
    payment = payment_service.get_payment(db, current_user, payment_id)
    return PaymentResponse.model_validate(payment)
