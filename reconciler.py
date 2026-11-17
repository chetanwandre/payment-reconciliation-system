from decimal import Decimal, InvalidOperation
import pandas as pd

TX_REQUIRED = {"transaction_id", "transaction_date", "amount", "currency", "type"}
BANK_REQUIRED = {"settlement_id", "transaction_id", "settlement_date", "amount", "currency"}

def _money(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"Invalid monetary amount: {value!r}")

def _validate(df, required, label):
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(sorted(missing))}")
    if df.empty:
        return
    if df[list(required)].isnull().any().any():
        raise ValueError(f"{label} contains blank required values.")
    for col in ("amount",):
        for value in df[col]:
            _money(value)

def generate_demo_data():
    tx = pd.DataFrame([
        ["T100", "2026-10-28", 100.00, "USD", "payment", ""],
        ["T101", "2026-10-29", 50.00, "USD", "payment", ""],
        ["T102", "2026-10-30", 20.00, "USD", "payment", ""],
        ["T103", "2026-10-30", 10.00, "USD", "payment", ""],
        ["T103", "2026-10-30", 10.00, "USD", "payment", ""], # duplicate platform row
        ["T104", "2026-10-31", 30.00, "USD", "payment", ""],
        ["R200", "2026-10-31", -5.00, "USD", "refund", "T999"], # unmatched original
        ["T105", "2026-10-31", 12.00, "USD", "payment", ""],
        ["T106", "2026-10-31", 8.00, "USD", "payment", ""],
        ["E201", "2026-10-29", 10.00, "EUR", "payment", ""],
        ["E202", "2026-10-30", 10.00, "EUR", "payment", ""],
        ["E203", "2026-10-31", 10.00, "EUR", "payment", ""],
    ], columns=["transaction_id", "transaction_date", "amount", "currency", "type", "original_transaction_id"])
    bank = pd.DataFrame([
        ["S100", "T100", "2026-10-29", 100.00, "USD"],
        ["S101", "T101", "2026-11-01", 50.00, "USD"], # following month
        ["S102", "T102", "2026-10-31", 19.99, "USD"], # within tolerance
        ["S103", "T103", "2026-10-31", 10.00, "USD"],
        ["S103-DUP", "T103", "2026-10-31", 10.00, "USD"], # duplicate settlement for transaction
        ["S104", "T104", "2026-10-31", 30.00, "USD"],
        ["S106", "T106", "2026-10-31", 8.00, "USD"],
        ["S999", "T999-BANK-ONLY", "2026-10-31", 4.00, "USD"], # bank-only
        ["E-S201", "E201", "2026-10-30", 9.995, "EUR"],
        ["E-S202", "E202", "2026-10-31", 9.995, "EUR"],
        ["E-S203", "E203", "2026-10-31", 9.995, "EUR"],
    ], columns=["settlement_id", "transaction_id", "settlement_date", "amount", "currency"])
    return tx, bank

def reconcile(transactions, settlements, tolerance=0.01):
    tx, bank = transactions.copy(), settlements.copy()
    _validate(tx, TX_REQUIRED, "Transactions")
    _validate(bank, BANK_REQUIRED, "Settlements")
    if tolerance < 0:
        raise ValueError("Tolerance cannot be negative.")
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="raise")
    bank["settlement_date"] = pd.to_datetime(bank["settlement_date"], errors="raise")
    tx["amount"] = tx["amount"].map(_money)
    bank["amount"] = bank["amount"].map(_money)
    tx["type"] = tx["type"].astype(str).str.lower().str.strip()
    tx["currency"] = tx["currency"].astype(str).str.upper().str.strip()
    bank["currency"] = bank["currency"].astype(str).str.upper().str.strip()
    tol = Decimal(str(tolerance))
    issues = []

    def add(issue, record, details):
        issues.append({"issue_type": issue, "record_id": str(record), "details": details})

    for tid, group in tx.groupby("transaction_id"):
        if len(group) > 1:
            add("duplicate_platform_transaction", tid, f"Found {len(group)} platform rows for this transaction ID.")
    for sid, group in bank.groupby("settlement_id"):
        if len(group) > 1:
            add("duplicate_bank_settlement_id", sid, f"Found {len(group)} bank rows for this settlement ID.")
    for tid, group in bank.groupby("transaction_id"):
        if len(group) > 1:
            add("multiple_settlements_for_transaction", tid, f"Found {len(group)} settlement rows for this transaction ID.")

    tx_ids = set(tx["transaction_id"].astype(str))
    bank_ids = set(bank["transaction_id"].astype(str))
    for _, row in tx.iterrows():
        if row["type"] == "refund":
            original = str(row.get("original_transaction_id", "")).strip()
            if not original or original.lower() == "nan" or original not in tx_ids:
                add("refund_without_matching_original", row["transaction_id"], f"Refund references missing original transaction {original!r}.")
            continue
        matches = bank[bank["transaction_id"].astype(str) == str(row["transaction_id"])]
        if matches.empty:
            add("missing_settlement", row["transaction_id"], "Platform transaction has no bank settlement.")
            continue
        # Use all matches for duplicate detection, but compare the first row to avoid silently summing duplicates.
        b = matches.iloc[0]
        if row["currency"] != b["currency"]:
            add("currency_mismatch", row["transaction_id"], f"Platform currency {row['currency']} differs from bank currency {b['currency']}.")
            continue
        delta = b["amount"] - row["amount"]
        if abs(delta) > tol:
            add("amount_mismatch", row["transaction_id"], f"Platform {row['amount']} vs bank {b['amount']} (difference {delta}).")
        if b["settlement_date"].to_period("M") > row["transaction_date"].to_period("M"):
            add("settled_following_month", row["transaction_id"], f"Transaction date {row['transaction_date'].date()}; settlement date {b['settlement_date'].date()}.")

    for _, row in bank.iterrows():
        if str(row["transaction_id"]) not in tx_ids:
            add("bank_settlement_without_platform_transaction", row["settlement_id"], f"Bank settlement references unknown transaction {row['transaction_id']}.")

    # Aggregate control totals, by currency, excluding refund rows from payment-side total.
    currencies = sorted(set(tx["currency"]) | set(bank["currency"]))
    control_rows = []
    for cur in currencies:
        platform = sum((x for x in tx.loc[(tx.currency == cur) & (tx.type != "refund"), "amount"]), Decimal("0"))
        bank_total = sum((x for x in bank.loc[bank.currency == cur, "amount"]), Decimal("0"))
        residual = bank_total - platform
        # Only classify as an aggregate rounding gap if each matched payment's difference is within tolerance,
        # while the aggregate residual exceeds tolerance.
        matched_diffs = []
        for _, row in tx[(tx.currency == cur) & (tx.type != "refund")].iterrows():
            found = bank[(bank.currency == cur) & (bank.transaction_id.astype(str) == str(row.transaction_id))]
            if len(found) == 1:
                matched_diffs.append(abs(found.iloc[0]["amount"] - row["amount"]))
        if matched_diffs and all(d <= tol for d in matched_diffs) and abs(residual) > tol:
            add("aggregate_rounding_difference", cur, f"Aggregate bank-platform residual is {residual} {cur}, although individual matched differences are within tolerance.")
        control_rows.append({"currency": cur, "platform_payments_total": str(platform), "bank_settlements_total": str(bank_total), "bank_minus_platform": str(residual)})
    exceptions = pd.DataFrame(issues, columns=["issue_type", "record_id", "details"])
    control = pd.DataFrame(control_rows)
    return {"exceptions": exceptions, "control_totals": control,
            "summary": {"currencies": len(currencies)}}
