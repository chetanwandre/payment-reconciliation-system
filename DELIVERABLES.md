# Assessment submission pack

This repository supplies the working prototype, generated data, test cases, assumptions, prompts, and a demo recording plan.

## 1. Brainstorming thread (working design log)

**User goal:** Reconcile a payment platform's transaction ledger to bank settlements and explain month-end gaps.

**Assistant:** The key is to avoid treating every mismatch as the same problem. I propose a row-level matching pass plus a currency-level control-total pass. Row-level checks catch missing/duplicate/mismatched records; control totals catch residuals that are not obvious on a single row.

**User:** The prompt specifically calls out next-month settlement, aggregate rounding, duplicate entries, and orphan refunds.

**Assistant:** I will make each of those an explicit exception type and generate synthetic data that demonstrates each case. I will also include missing settlements, bank-only records, amount/currency mismatches, because they are natural reconciliation controls.

**User:** What assumptions should be named?

**Assistant:** State the settlement cutoff, one-to-one matching assumption, currency handling, tolerance, refund lineage, and treatment of fees/partial settlements. The prototype will flag multi-settlement records rather than silently summing them.

**User:** How should results be presented?

**Assistant:** Provide an exception register with record ID and explanation, plus currency-level control totals and CSV downloads. An exception is an investigation lead, not an automatic adjustment.

**User:** How do we verify it?

**Assistant:** Unit tests should prove each required exception can be detected, test the tolerance boundary, and verify invalid schemas fail clearly.

## 2. Distilled prompt

Build a small, runnable payment reconciliation application. It must accept platform transaction CSV and bank settlement CSV files, generate demo data when no files are supplied, match records by transaction ID, and report: settlements in the following month, aggregate rounding differences that appear only at currency-total level, duplicate platform entries, and refunds without matching originals. Also detect missing settlements, bank-only records, multiple settlements per transaction, amount mismatches, and currency mismatches. Use Decimal-safe amount comparisons, configurable per-transaction tolerance, explainable exception rows, currency-level control totals, downloadable CSV reports, clear input validation, automated tests, a README, and explicit assumptions. Do not silently net duplicates or infer FX/fees/partial settlements.

## 3. Raw prompt (copy into Claude Code / Cursor)

You are a senior engineer helping implement a payment reconciliation prototype for an assessment. Build a Streamlit application in Python that compares a payments platform ledger with bank settlement records. The assessment states: (a) a platform records a transaction instantly when a customer pays; (b) the bank batches and settles funds 1–2 days later; (c) month-end transactions should have matching settlements; (d) deliberately demonstrate a settlement in the following month, a rounding difference visible only when summed, a duplicate in one dataset, and a refund with no matching original. Generate your own sample data. State assumptions explicitly. Required deliverables: runnable working app, source code, tests, README, and a clear list of production risks. The app should upload CSVs, validate schemas, match by transaction ID, use Decimal for money, apply a configurable tolerance, report exception types and record-level explanations, show currency control totals, and allow CSV downloads. Include tests for each required gap and invalid input. Do not claim that a prototype is production-ready. Flag ambiguous cases rather than silently making accounting decisions.

## 4. Claude Code execution thread — capture the real thread before submission

The following is a **runbook, not a claim that Claude Code was actually run**. Paste the raw prompt above into Claude Code with this repository open, then preserve its actual conversation/export for the assessment.

Suggested sequence:
1. `Inspect the repository and summarize the reconciliation requirements before editing.`
2. `Implement the matching logic and demo dataset. Explain how each of the four required gap types is represented.`
3. `Build the Streamlit UI with uploads, exception table, control totals, and downloads.`
4. `Run pytest. Fix failures and show the final test output.`
5. `Review for accounting edge cases: duplicate handling, refunds, partial settlements, fees, time zones, currency precision, and late settlement files. Do not silently assume these are solved.`
6. `Update README with run instructions, schemas, assumptions, and production risks.`

Attach screenshots or the exported actual Claude Code transcript after completing those steps. Do not submit this runbook as if it were an actual execution log.

## 5. Test cases

| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | Platform transaction settles in next calendar month | `settled_following_month` |
| TC-02 | Duplicate platform transaction ID | `duplicate_platform_transaction` |
| TC-03 | Two bank rows reference one transaction | `multiple_settlements_for_transaction` |
| TC-04 | Refund references nonexistent original | `refund_without_matching_original` |
| TC-05 | Platform payment has no bank row | `missing_settlement` |
| TC-06 | Bank row references unknown platform ID | `bank_settlement_without_platform_transaction` |
| TC-07 | Amount difference exceeds tolerance | `amount_mismatch` |
| TC-08 | Difference equals one-cent default tolerance | no `amount_mismatch` |
| TC-09 | Required column absent | clear validation error |
| TC-10 | Currency differs across matched records | `currency_mismatch` |

## 6. Working output

Run `streamlit run app.py`. The application is locally runnable and includes generated demo data. A public deployment URL is not included because deployment requires access to a hosting account and its credentials. Deploy this repository to Streamlit Community Cloud or another approved host, then paste the resulting URL into the submission.

## 7. Demo video plan (record 2–3 minutes)

1. Open the deployed app or local Streamlit URL.
2. Click **Load generated demo data** and point out the platform and bank tables.
3. Click **Run reconciliation**.
4. Show the exception breakdown and click through the exception table, highlighting next-month settlement, duplicate transaction, and orphan refund.
5. Show the currency-level control totals and download both CSV reports.
6. End by stating that exceptions are investigation leads and that partial settlements, fees, FX, and cutoff policy need production decisions.

## 8. Three production-risk sentences

Production results could be wrong if bank files arrive late, timestamps use inconsistent time zones, or the settlement cutoff and grace period are not explicitly defined. Legitimate split settlements, fees, chargebacks, reversals, foreign-exchange conversions, and currency-specific precision can look like unexplained gaps unless modeled as first-class transaction types. Duplicate or incomplete source files and automated adjustments create financial-control risk, so ingestion must be idempotent, every result must be auditable, and a human must approve ledger corrections.
