import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request
from decimal import Decimal


BASE_URL = "http://127.0.0.1:8000"
INITIAL_BALANCE = Decimal("100.00")
DEBIT_AMOUNT = Decimal("10.00")
CONCURRENT_REQUESTS = 50


def request(method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.getcode(), json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else {}


def wait_for_service() -> None:
    for _ in range(20):
        try:
            status_code, _ = request("GET", "/openapi.json")
            if status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError("Service is not reachable at http://127.0.0.1:8000")


def run_debit(user_id: str, token: str) -> tuple[int, dict]:
    return request("POST", f"/wallets/{user_id}/debit", {"amount": str(DEBIT_AMOUNT)}, token=token)


def main() -> int:
    username = f"phase2_user_{int(time.time() * 1000)}"
    password = "pass123"

    wait_for_service()

    status_code, body = request("POST", "/auth/register", {"username": username, "password": password})
    if status_code != 201:
        print("Registration failed:", status_code, body)
        return 1
    user_id = str(body["id"])

    status_code, body = request("POST", "/auth/login", {"username": username, "password": password})
    if status_code != 200:
        print("Login failed:", status_code, body)
        return 1
    token = body["access_token"]

    status_code, body = request("POST", "/wallets", {"user_id": user_id}, token=token)
    if status_code != 201:
        print("Wallet creation failed:", status_code, body)
        return 1

    status_code, body = request("POST", f"/wallets/{user_id}/credit", {"amount": str(INITIAL_BALANCE)}, token=token)
    if status_code != 200:
        print("Initial credit failed:", status_code, body)
        return 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
        futures = [executor.submit(run_debit, user_id, token) for _ in range(CONCURRENT_REQUESTS)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    success_count = sum(1 for status_code, _ in results if status_code == 200)
    failed_count = sum(1 for status_code, _ in results if status_code == 400)
    unexpected = [(status_code, body) for status_code, body in results if status_code not in {200, 400}]

    balance_status, balance_body = request("GET", f"/wallets/{user_id}/balance", token=token)
    tx_status, tx_body = request("GET", f"/wallets/{user_id}/transactions", token=token)
    if balance_status != 200 or tx_status != 200:
        print("Failed to fetch final state:", balance_status, balance_body, tx_status, tx_body)
        return 1

    final_balance = Decimal(balance_body["balance"])
    debit_entries = [entry for entry in tx_body if entry["entry_type"] == "debit"]
    credit_entries = [entry for entry in tx_body if entry["entry_type"] == "credit"]

    expected_success = int(INITIAL_BALANCE / DEBIT_AMOUNT)
    expected_balance = INITIAL_BALANCE - (DEBIT_AMOUNT * success_count)

    print(f"Test wallet user_id: {user_id}")
    print(f"Successful debits: {success_count}")
    print(f"Failed debits: {failed_count}")
    print(f"Final balance: {final_balance}")
    print(f"Debit ledger entries: {len(debit_entries)}")
    print(f"Credit ledger entries: {len(credit_entries)}")

    if unexpected:
        print("Unexpected responses:", unexpected)
        return 1
    if success_count != expected_success:
        print(f"Expected {expected_success} successful debits.")
        return 1
    if failed_count != CONCURRENT_REQUESTS - expected_success:
        print(f"Expected {CONCURRENT_REQUESTS - expected_success} failed debits.")
        return 1
    if final_balance != expected_balance or final_balance != Decimal("0.00"):
        print("Final balance is incorrect.")
        return 1
    if len(debit_entries) != success_count:
        print("Debit ledger entries do not match successful debits.")
        return 1
    if len(credit_entries) != 1:
        print("Expected exactly one initial credit entry.")
        return 1

    print("Concurrency test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
