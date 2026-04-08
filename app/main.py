from decimal import Decimal
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, SessionLocal, engine
from app.models import LedgerEntry, Wallet
from app.schemas import (
    AmountRequest,
    BalanceResponse,
    CreateWalletRequest,
    LedgerEntryResponse,
    WalletResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()


@app.post("/wallets", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(payload: CreateWalletRequest, db: AsyncSession = Depends(get_db)):
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
    entry = LedgerEntry(
        wallet_id=wallet.id,
        entry_type=entry_type,
        amount=amount,
        balance_after=wallet.balance,
    )
    return entry


@app.post("/wallets/{user_id}/credit", response_model=WalletResponse)
async def credit_wallet(user_id: str, payload: AmountRequest, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        wallet = await get_wallet_for_update(db, user_id)
        wallet.balance += payload.amount
        db.add(create_ledger_entry(wallet, "credit", payload.amount))
    await db.refresh(wallet)
    return wallet


@app.post("/wallets/{user_id}/debit", response_model=WalletResponse)
async def debit_wallet(user_id: str, payload: AmountRequest, db: AsyncSession = Depends(get_db)):
    async with db.begin():
        wallet = await get_wallet_for_update(db, user_id)
        if wallet.balance < payload.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance.")

        wallet.balance -= payload.amount
        db.add(create_ledger_entry(wallet, "debit", payload.amount))
    await db.refresh(wallet)
    return wallet


@app.get("/wallets/{user_id}/balance", response_model=BalanceResponse)
async def get_wallet_balance(user_id: str, db: AsyncSession = Depends(get_db)):
    wallet = (await db.execute(select(Wallet).where(Wallet.user_id == user_id))).scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found.")
    return BalanceResponse(user_id=wallet.user_id, balance=wallet.balance)


@app.get("/wallets/{user_id}/transactions", response_model=list[LedgerEntryResponse])
async def get_transaction_history(user_id: str, db: AsyncSession = Depends(get_db)):
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
