## IDRE-558: Refunds should not make it to banking dashboard without refund information on file

**Jira Ticket:** [IDRE-558](https://orchidsoftware.atlassian.net//browse/IDRE-558)

## Summary
This plan addresses the issue of refunds appearing on the banking dashboard without banking information by implementing a three-pronged approach. First, it strengthens the server-side validation in `lib/utils/payment-banking-validation.ts` to ensure refunds with empty banking details cannot be approved. Second, it updates the data-fetching query in `lib/actions/payment-approvals.ts` to filter out any existing invalid refund records from the banking dashboard view. Finally, it verifies that the existing client-side alert on the payments dashboard correctly warns the user, which will now be backed by the stricter server-side validation.

## Implementation Plan

**Step 1: Strengthen Server-Side Banking Info Validation**  
In the `validateRefundBankingInfo` function, strengthen the validation for `bankingSnapshot`. Instead of just checking for null/undefined, ensure the object is not empty and contains required fields. This can be done by checking `Object.keys(payment.bankingSnapshot).length > 0` or, more robustly, by verifying the presence of essential properties like `accountNumberLast4` or `routingNumberLast4`, similar to the client-side check.
Files: `lib/utils/payment-banking-validation.ts`

**Step 2: Filter Invalid Refunds from Banking Dashboard View**  
In the `getApprovedPayments` function, modify the Prisma query's `whereClause.NOT` condition around line 939. The current check for `{ bankingSnapshot: { equals: Prisma.DbNull } }` is insufficient as it allows payments with an empty JSON object `{}` to be displayed. Update the condition to exclude payments where `bankingSnapshot` is either null OR an empty object. This will filter out existing invalid records from the Banking Dashboard. The updated logic should look like this: `{ OR: [{ bankingSnapshot: { equals: Prisma.DbNull } }, { bankingSnapshot: { equals: {} as Prisma.InputJsonValue } }] }` within the existing `AND` block.
Files: `lib/actions/payment-approvals.ts`

**Step 3: Verify Client-Side Validation Alert**  
Verify that the existing logic in the `handleApprove` function (around line 1324) correctly uses the `getBankingInfoError` utility to display a toast error and prevent the `approvePaymentFirstStage` action from being called if banking information is missing. No code changes are anticipated for this file as the functionality already exists and will be correctly enforced by the server-side changes.
Files: `app/dashboard/payments/payments-client.tsx`

**Risk Level:** LOW — The changes are narrowly focused on validation and data filtering logic for refunds. The primary risk is an incorrect Prisma query syntax for checking an empty JSON object, which would be caught during development and testing. The core business logic for payments is not being altered.

## Proposed Code Changes

### `lib/utils/payment-banking-validation.ts` (modify)
The original validation for `bankingSnapshot` only checked for `null` or `undefined`. This allowed payments with an empty JSON object (`{}`) to pass validation, leading to them appearing on the banking dashboard without data. This change strengthens the check to ensure the `bankingSnapshot` is a non-empty object, which correctly prevents approval of refunds with incomplete banking information.
```typescript
--- a/lib/utils/payment-banking-validation.ts
+++ b/lib/utils/payment-banking-validation.ts
@@ -50,8 +50,9 @@
     payment.outgoingBankId || payment.outgoingBankAccount?.id
   );
   const hasSnapshot =
-    payment.bankingSnapshot !== null &&
-    payment.bankingSnapshot !== undefined;
+    payment.bankingSnapshot !== null &&
+    typeof payment.bankingSnapshot === "object" &&
+    Object.keys(payment.bankingSnapshot).length > 0;
 
   if (!hasOutgoingBank && !hasSnapshot) {
     return "Cannot approve refund for NACHA processing: missing ACH banking information (Bank Name, Routing #, Account #). The party must have banking details on file before this refund can be approved.";
```

### `lib/actions/payment-approvals.ts` (modify)
The Prisma query in `getApprovedPayments` was only filtering out refunds where the `bankingSnapshot` field was explicitly `NULL` in the database. It did not account for records where the field contained an empty JSON object (`{}`), causing them to be incorrectly displayed on the banking dashboard. This change updates the query to exclude records where `bankingSnapshot` is either `NULL` or an empty object, ensuring that only refunds with valid banking data are fetched for the dashboard.
```typescript
--- a/lib/actions/payment-approvals.ts
+++ b/lib/actions/payment-approvals.ts
@@ -936,13 +936,18 @@
           { paymentMethod: "CHECK" },
         ],
       },
-      // Exclude ACH refunds missing banking information
+      // Exclude ACH refunds missing banking information (null or empty object)
       {
         AND: [
           { direction: "OUTGOING" },
           { type: { in: BANKING_REFUND_TYPES } },
           { paymentMethod: { not: "CHECK" } },
           { outgoingBankId: null },
-          { bankingSnapshot: { equals: Prisma.DbNull } },
+          {
+            OR: [
+              { bankingSnapshot: { equals: Prisma.DbNull } },
+              { bankingSnapshot: { equals: {} as Prisma.InputJsonValue } },
+            ],
+          },
         ],
       },
     ];
```

**New Dependencies:**
- `No new dependencies are needed.`

## Test Suggestions

Framework: `Jest`

- **shouldReturnFalseForEmptyBankingSnapshotObject** *(edge case)* — This is the primary regression test for the bug. It ensures that a payment with an empty banking snapshot object is considered invalid, which was the cause of the original issue.
- **shouldReturnFalseForNullBankingSnapshot** *(edge case)* — Verifies that the validation correctly handles `null` values for the banking snapshot, which is a common boundary condition.
- **shouldReturnTrueForValidBankingSnapshot** — Tests the happy path to ensure that valid payment objects are still correctly identified and processed.
- **getApprovedPaymentsShouldFilterOutPaymentsWithInvalidSnapshots** — This test ensures the data-fetching layer for the Banking Dashboard correctly filters out the invalid records at the database query level, preventing them from ever reaching the UI.
- **shouldShowAlertAndPreventApprovalForPaymentWithMissingBankingInfo** — Verifies the third acceptance criteria: "Add a validation check during the 'Approve' action on the Payments Dashboard to alert users if ACH info is missing." This ensures the UI provides immediate feedback and prevents invalid state transitions.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This document outlines the foundational business rule that banking information must be explicitly tied to a verified Organization record before any payment or refund can be processed. The ticket addresses a failure to enforce this rule. Section 10.1 also details the intended data model, including a 'banking_verified' flag.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This page details the specific end-to-end "happy path" workflow for refunds that the ticket is trying to fix. It confirms the expected sequence of events: a refund is created, then approved in the Payment Dashboard, and only then should it be ready for NACHA file generation in the Banking tab.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document provides critical context for the developer, identifying that the Banking Dashboard and NACHA generation pipeline are known fragile areas of the application. It highlights that incorrect banking information is a recurring root cause for high-severity production issues, underscoring the importance of the validation requested in the ticket.

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