# Wallet Ledger Service

## Prerequisites

- Python 3.11
- PostgreSQL
- Database: `wallet_ledger_db`

## Project Setup

1. Create the virtual environment:

```powershell
py -3.11 -m venv .venv
```

2. Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Make sure the `.env` file contains:

```env
DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5432/wallet_ledger_db
```

## Run the Application

```powershell
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /wallets`
- `POST /wallets/{user_id}/credit`
- `POST /wallets/{user_id}/debit`
- `GET /wallets/{user_id}/balance`
- `GET /wallets/{user_id}/transactions`
