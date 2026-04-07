from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CreateWalletRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)


class AmountRequest(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)


class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    balance: Decimal
    created_at: datetime


class BalanceResponse(BaseModel):
    user_id: str
    balance: Decimal


class LedgerEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_type: str
    amount: Decimal
    balance_after: Decimal
    created_at: datetime
