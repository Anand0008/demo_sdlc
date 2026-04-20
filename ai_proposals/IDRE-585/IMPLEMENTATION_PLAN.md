## IDRE-585: Invoice Issues

**Jira Ticket:** [IDRE-585](https://orchidsoftware.atlassian.net//browse/IDRE-585)

## Summary
This plan addresses a bug where not all disputes awaiting payment are correctly displayed to the user, leading to inconsistencies between the payment list, CSV downloads, and overview counts. The root cause is identified as incorrect filtering in `lib/actions/party-payments.ts`, where cases in a defaulted status are being hidden if they are associated with an old, unpaid invoice.

The fix involves modifying the `hasActiveInvoice` logic within two functions in `lib/actions/party-payments.ts` (`getCasesForPayment` and the near-identical `getPaymentQueueStats`). The change will expand an existing exception to ensure that cases with `CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, or `CLOSED_DEFAULT_NIP` statuses are always shown as needing payment, regardless of any associated pending invoices. This will align the UI, CSV export, and overview stats, and ensure the invoice lifecycle behaves consistently for all dispute types as described in the ticket.

## Implementation Plan

**Step 1: Update `hasActiveInvoice` logic in `getCasesForPayment`**  
In the `getCasesForPayment` function, locate the `hasActiveInvoice` helper logic within the `cases.forEach` loop (around line 690). Modify the conditional check that currently bypasses the active invoice block for ineligible cases. Extend this condition to also include cases with statuses `CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, and `CLOSED_DEFAULT_NIP`. This will ensure that cases that have defaulted still appear in the payment list to settle remaining fees, even if they are attached to an old, unpaid invoice.
Files: `lib/actions/party-payments.ts`

**Step 2: Update `hasActiveInvoice` logic in `getPaymentQueueStats` to match**  
In the `getPaymentQueueStats` function, locate the duplicated `hasActiveInvoice` logic inside the `for (const case_ of batchCases)` loop (around line 1295). Apply the same modification as in the previous step to the conditional check for ineligible cases (around line 1307). Add `CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, and `CLOSED_DEFAULT_NIP` to this condition. This ensures that the payment overview statistics are calculated using the same logic as the main payment list, resolving the discrepancy between the count of cases awaiting payment and the cases shown in the payments tab.
Files: `lib/actions/party-payments.ts`

**Risk Level:** LOW — The change is confined to a single server-side action file and modifies filtering logic that is already conditioned on case status. The risk of unintended side effects is low, as it broadens an existing exception for terminal case statuses. The logic is duplicated, so care must be taken to apply the fix in both places, but the change itself is straightforward.

## Proposed Code Changes

### `lib/actions/party-payments.ts` (modify)
This change modifies the `hasActiveInvoice` logic in both `getCasesForPayment` and the nearly identical `getPaymentQueueStats`. It extends an existing exception to ensure that cases with defaulted statuses (`CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, `CLOSED_DEFAULT_NIP`) are always considered as needing payment, regardless of any associated pending invoices. This aligns the payment list, CSV export, and overview stats, resolving the inconsistency where these cases were incorrectly hidden from the user.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -703,8 +703,11 @@
         // should have been MISSING_BANK_INFO. They must never block payment.
         if (
           case_.status === "INELIGIBLE_PENDING_ADMIN_FEE" ||
-          case_.status === "INELIGIBLE"
+          case_.status === "INELIGIBLE" ||
+          case_.status === "CLOSED_DEFAULT" ||
+          case_.status === "CLOSED_DEFAULT_IP" ||
+          case_.status === "CLOSED_DEFAULT_NIP"
         ) {
           return false;
         }
@@ -1306,8 +1309,11 @@
 
                   if (
                     case_.status === "INELIGIBLE_PENDING_ADMIN_FEE" ||
-                    case_.status === "INELIGIBLE"
+                    case_.status === "INELIGIBLE" ||
+                    case_.status === "CLOSED_DEFAULT" ||
+                    case_.status === "CLOSED_DEFAULT_IP" ||
+                    case_.status === "CLOSED_DEFAULT_NIP"
                   ) {
                     return false;
                   }
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldIncludeDefaultedCasesEvenWithPendingInvoice** *(edge case)* — This is a regression test to reproduce the bug. It verifies that cases with a defaulted status are correctly included in the payment list, even when they are attached to an unpaid (pending) invoice. This ensures the fix works as intended.
- **shouldCountDefaultedCasesInStatsEvenWithPendingInvoice** *(edge case)* — This test verifies that the logic fix also applies to the statistics function, `getPaymentQueueStats`. It ensures that the overview counts shown to the user will match the contents of the payment list, fixing the data inconsistency.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the canonical, end-to-end lifecycle for a dispute, including the "Payments" phase. The ticket describes a failure in this process, where disputes are not behaving consistently. This document provides the baseline business process and status transitions (e.g., "Pending Payment") that the developer must correctly implement.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — The ticket's parent is "Organization Management," and this PRD explicitly states that flawed organization data is a root cause of "misdirected payments" and "workflow confusion." The developer needs to understand the planned architectural changes (e.g., parent/sub-organizations, explicit banking account binding) to ensure their fix for the invoicing logic aligns with the platform's strategic direction for data integrity.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page provides critical context by identifying "Invoicing & Invoice Acknowledgement" and "Organization & User Data Integrity" as major sources of bugs and operational pain. It helps the developer understand the systemic risks and common failure patterns associated with the feature they are fixing, which is essential for developing a robust solution.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This document outlines the expected "happy path" for the payment and invoicing workflow from a QA perspective. The ticket describes a scenario that deviates from this path. This provides the developer with a clear, step-by-step description of the functionality they need to restore, particularly around generating an invoice and having it appear correctly for acknowledgement.

**Suggested Documentation Updates:**

- IDRE Worflow
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._