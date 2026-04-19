## IDRE-585: Invoice Issues

**Jira Ticket:** [IDRE-585](https://orchidsoftware.atlassian.net//browse/IDRE-585)

## Summary
This plan resolves an inconsistency where certain disputes are not available for payment. The fix involves modifying the `getCasesForPayment` and `getPaymentQueueStats` functions in `lib/actions/party-payments.ts` to ignore active invoices for cases in default statuses (`CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, `CLOSED_DEFAULT_NIP`), similar to existing logic for ineligible cases. This will ensure that the list of cases available for payment is accurate, and that the UI, overview statistics, and CSV exports are all consistent. A shared helper function will be created to centralize this logic and prevent future discrepancies.

## Implementation Plan

**Step 1: Create a shared helper function for invoice exclusion logic**  
In `lib/actions/party-payments.ts`, create a new helper function `shouldIgnoreActiveInvoice` to centralize the logic for determining if an active invoice should be disregarded based on the case's status. This function will check if the case status is one of `INELIGIBLE_PENDING_ADMIN_FEE`, `INELIGIBLE`, `CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, or `CLOSED_DEFAULT_NIP`. This prevents code duplication and ensures consistency.
Files: `lib/actions/party-payments.ts`

**Step 2: Update `getCasesForPayment` to use the new helper function**  
In the `getCasesForPayment` function, locate the `hasActiveInvoice` constant. Replace the existing hardcoded status check (around line 704) with a call to the new `shouldIgnoreActiveInvoice` helper function. This will ensure that cases in default statuses are not blocked by existing invoices and will appear correctly in the 'Pay Online' list.
Files: `lib/actions/party-payments.ts`

**Step 3: Update `getPaymentQueueStats` to use the new helper function**  
In the `getPaymentQueueStats` function, locate the similar `hasActiveInvoice` constant. Replace its hardcoded status check (around line 1307) with a call to the same `shouldIgnoreActiveInvoice` helper function. This ensures that the payment overview statistics are calculated using the same logic as the main payment list, resolving data inconsistencies.
Files: `lib/actions/party-payments.ts`

**Risk Level:** LOW — The change is confined to a single server-side data-fetching file (`lib/actions/party-payments.ts`) and expands upon an existing, targeted logic pattern for status-based exclusions. The risk of unintended side effects is low as it only affects which cases are displayed for payment under specific, well-defined default statuses. The core payment processing logic remains untouched.

## Proposed Code Changes

### `lib/actions/party-payments.ts` (modify)
This change introduces a new helper function, `shouldIgnoreActiveInvoice`, to centralize the logic for determining when an active invoice should be ignored based on a case's status. The function includes the existing `INELIGIBLE` statuses and adds the `CLOSED_DEFAULT`, `CLOSED_DEFAULT_IP`, and `CLOSED_DEFAULT_NIP` statuses as required by the ticket.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -219,6 +219,20 @@
   };
 }
 
+function shouldIgnoreActiveInvoice(caseStatus: string | null | undefined): boolean {
+  if (!caseStatus) {
+    return false;
+  }
+  return [
+    "INELIGIBLE_PENDING_ADMIN_FEE",
+    "INELIGIBLE",
+    "CLOSED_DEFAULT",
+    "CLOSED_DEFAULT_IP",
+    "CLOSED_DEFAULT_NIP",
+  ].includes(caseStatus);
+}
+
 export async function getCasesForPayment(
   userId: string,
   organizationId?: string | null,
@@ -700,15 +714,12 @@
           return false;
         }
 
-        // Skip invoices for ineligible cases — these are legacy STANDARD invoices that
-        // should have been MISSING_BANK_INFO. They must never block payment.
-        if (
-          case_.status === "INELIGIBLE_PENDING_ADMIN_FEE" ||
-          case_.status === "INELIGIBLE"
-        ) {
+        // Skip invoices for certain case statuses (e.g., ineligible, default) — these
+        // are legacy STANDARD invoices that should have been MISSING_BANK_INFO or
+        // are for default-closed cases where payment is still required. They must
+        // never block payment.
+        if (shouldIgnoreActiveInvoice(case_.status)) {
           return false;
         }
 
@@ -1304,12 +1315,7 @@
                     return false;
                   }
 
-                  if (
-                    case_.status === "INELIGIBLE_PENDING_ADMIN_FEE" ||
-                    case_.status === "INELIGIBLE"
-                  ) {
+                  if (shouldIgnoreActiveInvoice(case_.status)) {
                     return false;
                   }
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldReturnTrueForClosedDefaultStatus** *(edge case)* — This test validates the core logic of the bug fix. It ensures that cases in a "CLOSED_DEFAULT" status are correctly identified, so they can be made available for payment regardless of any associated active invoices.
- **shouldReturnTrueForClosedDefaultIpStatus** *(edge case)* — This test covers another one of the default statuses ("CLOSED_DEFAULT_IP") added in the fix to ensure the logic applies to all relevant default states.
- **shouldReturnTrueForIneligibleStatus** *(edge case)* — This is a regression test to ensure that the pre-existing logic for "INELIGIBLE" cases has not been broken by the new changes.
- **shouldReturnFalseForStandardStatus** — This test verifies the "happy path" or default negative case, ensuring that the function correctly returns false for standard statuses that were never intended to be affected by this logic.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page provides the canonical business process for the entire dispute lifecycle. Step 3, 'Payments', explicitly states that the platform generates an administrative fee invoice, which moves the case into a 'Pending Payment' status. This is the direct business context for the ticket, which deals with disputes awaiting payment and the invoicing process.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document outlines the primary risk areas and common bug patterns in the platform. The sections on 'Invoicing & Invoice Acknowledgement' and 'Case Status & Workflow Transitions' are directly relevant. They highlight that the invoice lifecycle and its effect on case statuses are a known 'core risk' and a 'complexity hotspot', which is precisely what the developer is being asked to modify. This provides critical context about the fragility of the system.
- [Proposed Changes to Address Current Issues](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/246906881) — This page explicitly lists 'Invoice System Fixes' as a required area of work. The meeting notes also detail issues with incorrect case status changes and the need for 'structured admin closure workflows and guardrails to prevent inappropriate case status changes and ensure correct fee/refund handling'. This directly relates to the ticket's requirements for how creating and deleting invoices should modify the state of disputes in the payment tab.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This document provides the official end-to-end testing workflow for the QA team. Section 3, 'Payment & Party Portal', details the happy and unhappy path test cases for the invoicing process. This gives the developer a clear set of acceptance criteria and validation steps to follow to ensure their changes are working as expected within the established workflow.

**Suggested Documentation Updates:**

- IDRE Worflow: The description of the 'Payments' phase should be updated to clarify the specific state changes that occur when an invoice is created or deleted, detailing how disputes are removed from and returned to the payment queue.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: The E2E checklist should be updated to include specific test cases for verifying the 1:1 data match between an invoice and its corresponding CSV download, and for confirming that deleting an invoice correctly returns a dispute to the payment tab.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._