from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models import LedgerEntry, User, Wallet
from app.schemas import AmountRequest, BalanceResponse, CreateWalletRequest

logger = get_logger(__name__)
MAX_OPTIMISTIC_RETRIES = 100


async def create_user_wallet(db: AsyncSession, payload: CreateWalletRequest, current_user: User) -> Wallet:
    if payload.user_id != str(current_user.id):
        logger.warning(
            "Wallet creation blocked. current_user_id=%s requested_user_id=%s",
            current_user.id,
            payload.user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create another user's wallet.",
        )

    async with db.begin():
        existing_wallet = (
            await db.execute(select(Wallet).where(Wallet.user_id == payload.user_id))
        ).scalar_one_or_none()
        if existing_wallet:
            logger.warning("Wallet already exists for user_id=%s", payload.user_id)
            raise HTTPException(status_code=400, detail="Wallet already exists for this user.")

        wallet = Wallet(user_id=payload.user_id, balance=Decimal("0.00"), version=0)
        db.add(wallet)
    await db.refresh(wallet)
    logger.info("Wallet created successfully. wallet_id=%s user_id=%s", wallet.id, wallet.user_id)
    return wallet


async def get_wallet_by_user_id(db: AsyncSession, user_id: str) -> Wallet:
    wallet = (
        await db.execute(
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if wallet is None:
        logger.warning("Wallet not found. user_id=%s", user_id)
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
    for attempt in range(1, MAX_OPTIMISTIC_RETRIES + 1):
        wallet_id = None
        old_balance = None
        new_balance = None
        conflict_detected = False

        async with db.begin():
            wallet = await get_wallet_by_user_id(db, user_id)
            wallet_id = wallet.id
            old_balance = wallet.balance
            new_balance = wallet.balance + payload.amount

            result = await db.execute(
                update(Wallet)
                .where(Wallet.id == wallet.id, Wallet.version == wallet.version)
                .values(balance=new_balance, version=wallet.version + 1)
            )

            if result.rowcount != 1:
                conflict_detected = True
                logger.warning(
                    "Optimistic concurrency conflict on credit. user_id=%s attempt=%s version=%s",
                    user_id,
                    attempt,
                    wallet.version,
                )
            else:
                db.add(
                    LedgerEntry(
                        wallet_id=wallet.id,
                        entry_type="credit",
                        amount=payload.amount,
                        balance_after=new_balance,
                    )
                )

        if conflict_detected:
            continue

        updated_wallet = await get_wallet_by_user_id(db, user_id)
        logger.info(
            "Wallet credited successfully. user_id=%s amount=%s old_balance=%s new_balance=%s version=%s",
            user_id,
            payload.amount,
            old_balance,
            updated_wallet.balance,
            updated_wallet.version,
        )
        return updated_wallet

    logger.error("Credit failed after optimistic retries exhausted. user_id=%s", user_id)
    raise HTTPException(status_code=409, detail="Wallet update conflict. Please retry.")


async def debit_user_wallet(db: AsyncSession, user_id: str, payload: AmountRequest) -> Wallet:
    for attempt in range(1, MAX_OPTIMISTIC_RETRIES + 1):
        old_balance = None
        conflict_detected = False

        async with db.begin():
            wallet = await get_wallet_by_user_id(db, user_id)
            old_balance = wallet.balance
            if wallet.balance < payload.amount:
                logger.warning(
                    "Debit blocked due to insufficient balance. user_id=%s amount=%s current_balance=%s",
                    user_id,
                    payload.amount,
                    wallet.balance,
                )
                raise HTTPException(status_code=400, detail="Insufficient balance.")

            new_balance = wallet.balance - payload.amount
            result = await db.execute(
                update(Wallet)
                .where(Wallet.id == wallet.id, Wallet.version == wallet.version)
                .values(balance=new_balance, version=wallet.version + 1)
            )

            if result.rowcount != 1:
                conflict_detected = True
                logger.warning(
                    "Optimistic concurrency conflict on debit. user_id=%s attempt=%s version=%s",
                    user_id,
                    attempt,
                    wallet.version,
                )
            else:
                db.add(
                    LedgerEntry(
                        wallet_id=wallet.id,
                        entry_type="debit",
                        amount=payload.amount,
                        balance_after=new_balance,
                    )
                )

        if conflict_detected:
            continue

        updated_wallet = await get_wallet_by_user_id(db, user_id)
        logger.info(
            "Wallet debited successfully. user_id=%s amount=%s old_balance=%s new_balance=%s version=%s",
            user_id,
            payload.amount,
            old_balance,
            updated_wallet.balance,
            updated_wallet.version,
        )
        return updated_wallet

    logger.error("Debit failed after optimistic retries exhausted. user_id=%s", user_id)
    raise HTTPException(status_code=409, detail="Wallet update conflict. Please retry.")


async def get_user_wallet_balance(db: AsyncSession, user_id: str) -> BalanceResponse:
    wallet = await get_wallet_by_user_id(db, user_id)
    logger.info("Balance fetched for user_id=%s balance=%s", user_id, wallet.balance)
    return BalanceResponse(user_id=wallet.user_id, balance=wallet.balance)


async def get_user_transaction_history(db: AsyncSession, user_id: str) -> list[LedgerEntry]:
    wallet = await get_wallet_by_user_id(db, user_id)

    transactions = (
        await db.execute(
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet.id)
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
        )
    ).scalars()
    transactions_list = list(transactions)
    logger.info("Transaction history fetched for user_id=%s entries=%s", user_id, len(transactions_list))
    return transactions_list
