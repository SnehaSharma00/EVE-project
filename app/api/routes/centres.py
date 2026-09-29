from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.centre import CentreCreate, CentreResponse, CentreUpdate
from app.schemas.centre_test import CentreTestCreate, CentreTestResponse
from app.schemas.slot import SlotCreate, SlotResponse
from app.services.centre_service import centre_service

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.get(
    "",
    response_model=list[CentreResponse],
    status_code=status.HTTP_200_OK,
    summary="List diagnostic centres",
)
def list_centres(
    city: str | None = Query(default=None, description="Filter by city name"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Sequence[CentreResponse]:
    centres = centre_service.list_centres(
        db, city=city, is_active=is_active, skip=skip, limit=limit
    )
    return [CentreResponse.model_validate(c) for c in centres]


@router.get(
    "/{centre_id}",
    response_model=CentreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get centre by ID",
)
def get_centre(centre_id: int, db: Session = Depends(get_db)) -> CentreResponse:
    centre = centre_service.get_centre(db, centre_id)
    return CentreResponse.model_validate(centre)


@router.post(
    "",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create diagnostic centre",
)
def create_centre(
    centre_in: CentreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CentreResponse:
    centre = centre_service.create_centre(db, centre_in)
    return CentreResponse.model_validate(centre)


@router.patch(
    "/{centre_id}",
    response_model=CentreResponse,
    status_code=status.HTTP_200_OK,
    summary="Update diagnostic centre",
)
def update_centre(
    centre_id: int,
    centre_in: CentreUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CentreResponse:
    centre = centre_service.update_centre(db, centre_id, centre_in)
    return CentreResponse.model_validate(centre)


@router.get(
    "/{centre_id}/tests",
    response_model=list[CentreTestResponse],
    status_code=status.HTTP_200_OK,
    summary="List tests and prices at diagnostic centre",
)
def list_centre_tests(
    centre_id: int,
    is_available: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Sequence[CentreTestResponse]:
    centre_tests = centre_service.list_centre_tests(db, centre_id, is_available=is_available)
    return [CentreTestResponse.model_validate(ct) for ct in centre_tests]


@router.post(
    "/{centre_id}/tests",
    response_model=CentreTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Configure test and pricing at centre",
)
def add_centre_test(
    centre_id: int,
    centre_test_in: CentreTestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CentreTestResponse:
    centre_test = centre_service.add_test_to_centre(db, centre_id, centre_test_in)
    return CentreTestResponse.model_validate(centre_test)


@router.get(
    "/{centre_id}/slots",
    response_model=list[SlotResponse],
    status_code=status.HTTP_200_OK,
    summary="List appointment slots for centre",
)
def list_centre_slots(
    centre_id: int,
    is_available: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Sequence[SlotResponse]:
    slots = centre_service.list_slots(
        db, centre_id, is_available=is_available, skip=skip, limit=limit
    )
    return [SlotResponse.model_validate(s) for s in slots]


@router.post(
    "/{centre_id}/slots",
    response_model=SlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create appointment slot at centre",
)
def create_slot(
    centre_id: int,
    slot_in: SlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> SlotResponse:
    slot = centre_service.create_slot(db, centre_id, slot_in)
    return SlotResponse.model_validate(slot)
