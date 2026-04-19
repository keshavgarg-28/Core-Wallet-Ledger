from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LedgerEntry, User, Wallet
from app.schemas import AmountRequest, BalanceResponse, CreateWalletRequest


async def create_user_wallet(db: AsyncSession, payload: CreateWalletRequest, current_user: User) -> Wallet:
    if payload.user_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create another user's wallet.",
        )

    async with db.begin():
        existing_wallet = (
            await db.execute(select(Wallet).where(Wallet.user_id == payload.user_id))
        ).scalar_one_or_none()
        if existing_wallet:
            raise HTTPException(status_code=400, detail="Wallet already exists for this user.")

        wallet = Wallet(user_id=payload.user_id, balance=Decimal("0.00"))
        db.add(wallet)
    await db.refresh(wallet)
    return wallet


async def get_wallet_for_update(db: AsyncSession, user_id: str) -> Wallet:
    wallet = (
        await db.execute(
            select(Wallet).where(Wallet.user_id == user_id).with_for_update()
        )
    ).scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found.")
    return wallet


def create_ledger_entry(wallet: Wallet, entry_type: str, amount: Decimal) -> LedgerEntry:
    return LedgerEntry(
        wallet_id=wallet.id,
        entry_type=entry_type,
        amount=amount,
        balance_after=wallet.balance,
    )


async def credit_user_wallet(db: AsyncSession, user_id: str, payload: AmountRequest) -> Wallet:
    async with db.begin():
        wallet = await get_wallet_for_update(db, user_id)
        wallet.balance += payload.amount
        db.add(create_ledger_entry(wallet, "credit", payload.amount))
    await db.refresh(wallet)
    return wallet


async def debit_user_wallet(db: AsyncSession, user_id: str, payload: AmountRequest) -> Wallet:
    async with db.begin():
        wallet = await get_wallet_for_update(db, user_id)
        if wallet.balance < payload.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance.")

        wallet.balance -= payload.amount
        db.add(create_ledger_entry(wallet, "debit", payload.amount))
    await db.refresh(wallet)
    return wallet


async def get_user_wallet_balance(db: AsyncSession, user_id: str) -> BalanceResponse:
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found.")
    return BalanceResponse(user_id=wallet.user_id, balance=wallet.balance)


async def get_user_transaction_history(db: AsyncSession, user_id: str) -> list[LedgerEntry]:
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found.")

    transactions = (
        await db.execute(
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet.id)
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
        )
    ).scalars()
    return list(transactions)
