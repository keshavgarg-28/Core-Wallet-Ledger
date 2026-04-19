from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.dependencies import get_authorized_user, get_db
from app.models import User
from app.schemas import (
    AmountRequest,
    BalanceResponse,
    CreateWalletRequest,
    LedgerEntryResponse,
    WalletResponse,
)
from app.services.wallet_service import (
    create_user_wallet,
    credit_user_wallet,
    debit_user_wallet,
    get_user_transaction_history,
    get_user_wallet_balance,
)

router = APIRouter(prefix="/wallets", tags=["wallets"])


@router.post("", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    payload: CreateWalletRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_user_wallet(db, payload, current_user)


@router.post("/{user_id}/credit", response_model=WalletResponse)
async def credit_wallet(
    user_id: str,
    payload: AmountRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authorized_user),
):
    return await credit_user_wallet(db, user_id, payload)


@router.post("/{user_id}/debit", response_model=WalletResponse)
async def debit_wallet(
    user_id: str,
    payload: AmountRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authorized_user),
):
    return await debit_user_wallet(db, user_id, payload)


@router.get("/{user_id}/balance", response_model=BalanceResponse)
async def get_wallet_balance(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authorized_user),
):
    return await get_user_wallet_balance(db, user_id)


@router.get("/{user_id}/transactions", response_model=list[LedgerEntryResponse])
async def get_transaction_history(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_authorized_user),
):
    return await get_user_transaction_history(db, user_id)
