# Payment Reconciliation & Gap Detection

A small Streamlit application that compares a payment platform's transaction ledger with bank settlement records.

## Run locally

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (usually http://localhost:8501). Click **Load generated demo data**, then **Run reconciliation**. You can also upload your own CSV files.

## CSV schemas

Transactions CSV required columns:
- `transaction_id`
- `transaction_date` (parseable date)
- `amount` (numeric; refunds are negative in the demo)
- `currency` (e.g. USD)
- `type` (`payment` or `refund`)
- `original_transaction_id` (optional column, required in practice to validate refund lineage)

Settlements CSV required columns:
- `settlement_id`
- `transaction_id`
- `settlement_date`
- `amount`
- `currency`

## Detected exception types

- `settled_following_month`
- `aggregate_rounding_difference`
- `duplicate_platform_transaction`
- `duplicate_bank_settlement_id`
- `multiple_settlements_for_transaction`
- `refund_without_matching_original`
- `missing_settlement`
- `amount_mismatch`
- `currency_mismatch`
- `bank_settlement_without_platform_transaction`

## Assumptions and limitations

1. The platform records a transaction at payment time; the bank settlement date is the date funds arrive.
2. A settlement in a later calendar month is reported, even if the delay is operationally expected. The user must decide whether it is a valid timing item or an exception.
3. One bank settlement row per transaction is assumed for amount matching. Multiple rows are flagged rather than automatically summed because they may be duplicates or legitimate split settlements.
4. Amounts are compared only within the same currency. FX conversion is not attempted.
5. The default per-transaction tolerance is 0.01 in the transaction currency. It is configurable in the UI.
6. Aggregate rounding is flagged only when individual matched differences are within tolerance and the currency-level total residual exceeds tolerance.
7. Refund lineage is checked using `original_transaction_id`; the prototype flags a missing original ID or an ID not present in the platform file.
8. The sample is a month-end snapshot. Real systems need a configurable settlement cutoff/grace period and a way to include late-arriving bank files.

## Tests

```bash
pytest -q
```

## Production hardening

Use immutable source snapshots, access controls, audit logs, idempotent ingestion, schema/version validation, timezone-aware timestamps, currency-specific decimal rules, and human approval before ledger adjustments. Add support for partial settlements, fees, chargebacks, reversals, and FX separately rather than treating them as unexplained differences.
