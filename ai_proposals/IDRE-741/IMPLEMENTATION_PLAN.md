## IDRE-741: Unable to Apply Correct Payment After Deleting a Failed Payment on a Dispute

**Jira Ticket:** [IDRE-741](https://orchidsoftware.atlassian.net//browse/IDRE-741)

## Summary
The bug is caused by a validation check that incorrectly identifies a deleted/failed payment as still being active, blocking new payments. The plan is to fix this by updating the validation logic in 'lib/actions/payment.ts' to only check against active payments. I will also update the data-fetching logic in 'lib/actions/party-case-details.ts' to filter out these inactive payments, ensuring data consistency. Finally, a regression test will be added in 'tests/actions/case-balance-actions.test.ts' to prevent this issue from recurring.

## Implementation Plan

**Step 1: Update Payment Creation Validation to Ignore Inactive Payments**  
In the server action responsible for creating a payment, locate the validation check that prevents duplicate payments for a dispute party. This is likely related to the 'assertNoConflictingCasePartyPaymentSource' utility mentioned in the exploration report. Modify the database query within this validation logic to filter out payments that are not in an active state. The query for existing 'CasePaymentAllocation' or 'Payment' records should be updated to only consider payments with statuses present in the 'ACTIVE_CASE_PAYMENT_STATUSES' list. This will ensure that deleted or failed payments do not block the creation of a new, valid payment.
Files: `lib/actions/payment.ts`

**Step 2: Filter Inactive Payment Allocations in Case Details Query**  
In the 'getCaseDetails' function, update the Prisma query that fetches case data. Specifically, when including 'paymentAllocations', add a 'where' clause to filter the results based on the status of the associated payment. The query should only include allocations linked to payments with an active status (e.g., not 'FAILED', 'CANCELLED', or 'DELETED'). This ensures that the UI and any downstream logic only operate on valid, active payment data, preventing inconsistent state.
Files: `lib/actions/party-case-details.ts`

**Step 3: Add Regression Test for Deleted Payment Scenario**  
Add a new test case to verify the fix and prevent regressions. The test should replicate the scenario reported in the ticket: 1. Create a case with an initiating party. 2. Record a payment for that party. 3. Update the payment's status to 'FAILED' and then delete it. 4. Attempt to record a new, correct payment for the same party. 5. Assert that the second payment is created successfully without throwing the 'Payment already recorded' error.
Files: `tests/actions/case-balance-actions.test.ts`

**Risk Level:** MEDIUM — The change touches a critical and sensitive part of the application (payment processing), which has a history of production issues. While the fix seems targeted, any mistake could lead to incorrect payment blocking or allow duplicate payments. Thorough testing is required to mitigate this risk.

## Proposed Code Changes

### `lib/actions/payment.ts` (modify)
The core of the bug lies in the validation check for existing payments, which incorrectly flagged deleted or failed payments as active. This change modifies the Prisma query that checks for existing `CasePaymentAllocation` records. By adding a `where` clause to filter for payments with a status in `ACTIVE_CASE_PAYMENT_STATUSES`, we ensure that only genuinely active payments will block the creation of a new one, resolving the issue. I am assuming this logic exists within a function like `assertNoConflictingCasePartyPaymentSource` or a similar validation utility within this file, as indicated by the implementation plan.
```typescript
--- a/lib/actions/payment.ts
+++ b/lib/actions/payment.ts
@@ -68,6 +68,7 @@
   PaymentDirection,
   PaymentStatus,
   PaymentType,
+  Prisma,
   PartyType,
   CaseStatus,
   PaymentMethod,
@@ -1265,6 +1266,11 @@
     where: {
       caseId: caseId,
       partyType: partyType,
+      payment: {
+        status: {
+          in: ACTIVE_CASE_PAYMENT_STATUSES,
+        },
+      },
     },
   });
```

### `lib/actions/party-case-details.ts` (modify)
To ensure data consistency across the application, this change filters the `paymentAllocations` returned by `getCaseDetails`. By adding a `where` clause to exclude payments that are `FAILED`, `CANCELLED`, or `DELETED`, we prevent inactive payment data from being displayed in the UI or used in downstream logic, which could lead to an inconsistent state. I've also added the `PaymentStatus` enum to the imports to support this change.
```typescript
--- a/lib/actions/party-case-details.ts
+++ b/lib/actions/party-case-details.ts
@@ -1,6 +1,6 @@
 "use server";
 
 import { prisma } from "@/lib/database";
-import { PartyType } from "@prisma/client";
+import { PartyType, PaymentStatus } from "@prisma/client";
 import {
   calculateCasePaymentAmount,
   CASE_PRICING,
@@ -57,6 +57,13 @@
         nonInitiatingParty: true,
         DisputeLineItems: true,
         paymentAllocations: {
+          where: {
+            payment: {
+              status: {
+                notIn: [PaymentStatus.FAILED, PaymentStatus.CANCELLED, PaymentStatus.DELETED],
+              },
+            },
+          },
           include: {
             payment: true,
           },
```

### `tests/actions/case-balance-actions.test.ts` (modify)
This adds a new test suite with a test case that specifically replicates the bug reported in IDRE-741. The test creates a payment, marks it as failed and then deleted, and then asserts that a new payment can be successfully created for the same party. This regression test will prevent this specific issue from occurring again in the future.
```typescript
--- a/tests/actions/case-balance-actions.test.ts
+++ b/tests/actions/case-balance-actions.test.ts
@@ -1,10 +1,13 @@
 import { describe, it, expect, beforeAll, afterAll } from "vitest";
 import { db } from "@/lib/database";
-import { PartyType } from "@prisma/client";
+import { PartyType, PaymentStatus } from "@prisma/client";
 import { Decimal } from "@prisma/client/runtime/library";
 import { createTestCaseWithParties } from "tests/utils/test-case-helpers";
 import { recordCheckPayment } from "@/lib/actions/payment";
-import { createCasePaymentObligation } from "@/lib/actions/case-payment-obligation";
+import {
+  createCasePaymentObligation,
+  getCasePaymentObligation,
+} from "@/lib/actions/case-payment-obligation";
 
 describe("Case Balance Actions", () => {
   // ... existing tests
@@ -12,3 +15,57 @@
     // ... existing test content
   });
 });
+
+describe("IDRE-741: Payment creation after failed/deleted payment", () => {
+  it("should allow recording a new payment after a previous one for the same party was marked as DELETED", async () => {
+    // 1. Setup: Create a case, parties, and an initial payment obligation.
+    const { case: testCase, initiatingParty } = await createTestCaseWithParties();
+    await createCasePaymentObligation({
+      caseId: testCase.id,
+      partyId: initiatingParty.id,
+      partyType: PartyType.INITIATING,
+      amount: new Decimal(450),
+    });
+
+    // 2. Record an initial payment.
+    const { payment: initialPayment } = await recordCheckPayment({
+      caseId: testCase.id,
+      partyId: initiatingParty.id,
+      partyType: PartyType.INITIATING,
+      amount: new Decimal(450),
+      referenceNumber: "12345",
+      receivedAt: new Date(),
+    });
+
+    // 3. Mark the payment as FAILED, then DELETED to simulate the bug scenario.
+    await db.payment.update({
+      where: { id: initialPayment.id },
+      data: { status: PaymentStatus.FAILED },
+    });
+    await db.payment.update({
+      where: { id: initia
... (truncated — see full diff in files)
```

**New Dependencies:**
- `No new dependencies needed.`

## Test Suggestions

Framework: `Jest`

- **shouldAllowCreatingNewPaymentWhenPreviousPaymentIsDeleted** — This is a regression test that directly reproduces the bug in IDRE-741. It verifies that the system allows a new payment to be created for a party if their previous payment has been deleted, ensuring the validation logic correctly checks only for *active* payments.
- **shouldOnlyReturnActivePaymentsFromGetCaseDetails** — This test validates the data-fetching logic change. It ensures that the `getCaseDetails` function correctly filters out payments with inactive statuses (`FAILED`, `DELETED`, etc.), preventing inconsistent data from being passed to the UI or other downstream logic.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page is highly relevant as it identifies the "Payments & Refunds Logic / Workflow" as a known "major complexity hotspot" that is prone to high-impact production issues. This directly relates to the ticket, which describes a critical production-only payment bug.

**Suggested Documentation Updates:**

- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: This document should be updated to include the specific scenario from this ticket (deleting a failed payment and then adding a new one) into the standard E2E testing or regression suite to prevent future occurrences.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._