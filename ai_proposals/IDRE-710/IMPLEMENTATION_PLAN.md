## IDRE-710: When user is performing admin closure if only IP/NIP paid for dispute status is getting changed to Closed

**Jira Ticket:** [IDRE-710](https://orchidsoftware.atlassian.net//browse/IDRE-710)

## Summary
This plan addresses a bug where cases are prematurely closed during administrative closure when only one party has paid. The root cause is that payments with a `PENDING` status are incorrectly considered as "paid".

The fix involves two steps:
1.  Update the `loadCaseFinancialState` function in `lib/services/administrative-closure.ts` to exclude `PENDING` payments when determining if a party has paid.
2.  Similarly, update the `/api/cases/[caseId]/payment-status/route.ts` API endpoint to exclude `PENDING` payments from its response.

These changes will ensure that a case remains in a pending closure state until payments from both parties are either `APPROVED` or `COMPLETED`, resolving the bug.

## Implementation Plan

**Step 1: Correct Payment Status Check in Case Financial State Service**  
In the `loadCaseFinancialState` function, modify the filter for `completedAllocations` to exclude payments with a `PENDING` status. The logic should only consider payments with `APPROVED` or `COMPLETED` statuses as paid. This will ensure the financial state accurately reflects cleared payments before allowing a case to be closed.
Files: `lib/services/administrative-closure.ts`

**Step 2: Correct Payment Status Check in API Endpoint**  
In the `GET` handler, update the logic for determining `initiatingPartyPaid` and `nonInitiatingPartyPaid`. Remove `PENDING` from the list of statuses considered as "paid". The check should only include `APPROVED` and `COMPLETED` statuses to prevent the UI from incorrectly showing that a payment is complete.
Files: `app/api/cases/[caseId]/payment-status/route.ts`

**Risk Level:** LOW — The change is a targeted bug fix that corrects the logic for checking payment statuses in two specific files. The logic is being aligned with what is already present in other parts of the codebase (e.g., `scripts/find-affected-cases.ts`). The risk of regression is low as it's a correction to a faulty condition.

## Proposed Code Changes

### `lib/services/administrative-closure.ts` (modify)
This change modifies `loadCaseFinancialState` to exclude payments with a `PENDING` status when determining if a party has paid. This ensures the financial state accurately reflects only cleared or approved payments, preventing premature case closure.
```typescript
--- a/lib/services/administrative-closure.ts
+++ b/lib/services/administrative-closure.ts
@@ -118,14 +118,13 @@
     lineItemCount
   );
 
-  // Determine party payments (Pending, Approved or Completed incoming case payments)
-  // Note: PENDING and APPROVED payments are considered "paid" because they've been submitted/approved
-  // and are awaiting processing. This matches the logic in payment.ts for case transitions.
+  // Determine party payments (Approved or Completed incoming case payments)
+  // Note: APPROVED payments are considered "paid" because they've been submitted/approved
+  // and are awaiting processing. PENDING payments are not considered paid for closure purposes.
   const completedAllocations = (theCase.paymentAllocations || []).filter(
     (alloc) =>
-      (alloc.payment?.status === PaymentStatus.PENDING ||
-        alloc.payment?.status === PaymentStatus.APPROVED ||
+      (alloc.payment?.status === PaymentStatus.APPROVED ||
         alloc.payment?.status === PaymentStatus.COMPLETED) &&
       alloc.payment?.type === PaymentType.CASE_PAYMENT &&
       alloc.payment?.direction === "INCOMING"
   );
```

### `app/api/cases/[caseId]/payment-status/route.ts` (modify)
This change updates the payment status API endpoint to no longer consider `PENDING` payments as paid. This aligns the API's logic with the backend services and prevents the UI from incorrectly indicating that a payment is complete before it is approved or cleared.
```typescript
--- a/app/api/cases/[caseId]/payment-status/route.ts
+++ b/app/api/cases/[caseId]/payment-status/route.ts
@@ -47,19 +47,17 @@
         Number(allocation.allocatedAmount) > 0 &&
         allocation.payment &&
         allocation.payment.direction === "INCOMING" &&
-        (allocation.payment.status === "PENDING" ||
-          allocation.payment.status === "APPROVED" ||
-          allocation.payment.status === "COMPLETED")
+        (allocation.payment.status === "APPROVED" ||
+          allocation.payment.status === "COMPLETED")
     );
 
     const nonInitiatingPartyPaid = caseData.paymentAllocations.some(
       (allocation) =>
         allocation.partyType === "NON_INITIATING" &&
         Number(allocation.allocatedAmount) > 0 &&
         allocation.payment &&
         allocation.payment.direction === "INCOMING" &&
-        (allocation.payment.status === "PENDING" ||
-          allocation.payment.status === "APPROVED" ||
-          allocation.payment.status === "COMPLETED")
+        (allocation.payment.status === "APPROVED" ||
+          allocation.payment.status === "COMPLETED")
     );
 
     return NextResponse.json({
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldReturnPartyAsUnpaidWhenTheirOnlyPaymentIsPending** *(edge case)* — This is the primary regression test to reproduce and validate the bug fix. It ensures that a payment with a "PENDING" status is correctly ignored when determining the financial state of a case, preventing premature closure.
- **shouldReturnBothPartiesAsPaidWhenPaymentsAreApprovedOrCompleted** — This test ensures that the change to ignore "PENDING" payments did not break the existing logic for valid, completed payments. It verifies the happy path where payments are correctly processed.
- **shouldReturnCorrectPaymentStatusWhenOnePartyHasPendingPayment** *(edge case)* — This integration test verifies that the API route correctly reflects the business logic change from the service layer. It ensures the UI will receive the correct payment status, preventing it from incorrectly showing a case as fully paid.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page provides the high-level, end-to-end case lifecycle, including the Payments and Closure phases. It confirms that an "Admin Closure Review" is the final step before a case is marked "Closed", which is the process described in the ticket.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document identifies that bugs related to payment logic and case status transitions are a known "pain point" and a "major complexity hotspot". It specifically recommends QA focus on the exact scenario in the ticket: "Both parties paid vs only one paid", confirming this is a critical and fragile area of the application.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This is the most critical document. It provides the detailed state machine for the case workflow, defining the exact statuses involved. It explicitly states that when one party pays, the case should move to `PENDING_SECOND_PAYMENT`. It also defines the "Administrative Closure Path", including the `PENDING_ADMINISTRATIVE_CLOSURE` status. This document contains the precise business logic that the ticket (IDRE-710) claims is being violated.

**Suggested Documentation Updates:**

- IDRE Case Workflow Documentation
- IDRE Worflow

## AI Confidence Scores
Plan: 100%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._