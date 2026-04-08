# Wallet Ledger Service

## Run the Application

```powershell
uvicorn app.main:app --reload
```

## Run Phase 2 Concurrency Test

```powershell
python scripts\phase2_concurrency_test.py
```

## API Endpoints

- `POST /wallets`
- `POST /wallets/{user_id}/credit`
- `POST /wallets/{user_id}/debit`
- `GET /wallets/{user_id}/balance`
- `GET /wallets/{user_id}/transactions`
