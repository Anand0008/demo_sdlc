## IDRE-558: Refunds should not make it to banking dashboard without refund information on file

**Jira Ticket:** [IDRE-558](https://orchidsoftware.atlassian.net//browse/IDRE-558)

## Summary
This implementation plan addresses the issue of refunds appearing on the Banking Dashboard without required banking information. The plan involves a three-step process: First, I will strengthen the core server-side validation utility (`lib/utils/payment-banking-validation.ts`) to correctly identify empty banking snapshots as invalid. Second, I will update the data-fetching actions (`getApprovedPayments` and `getPaymentsReadyForNacha` in `lib/actions/payment-approvals.ts`) to filter out these invalid refund records from being sent to the Banking Dashboard and NACHA generation views. Finally, I will verify that the Payments Dashboard UI (`app/dashboard/payments/payments-client.tsx`) correctly displays an error to the user when they attempt to approve a refund with missing banking details, leveraging the improved validation. This ensures that no new invalid refunds can be approved and existing ones are no longer displayed.

## Implementation Plan

**Step 1: Strengthen Banking Info Validation Utility**  
In the `validateRefundBankingInfo` function, modify the `hasSnapshot` constant to check if the `bankingSnapshot` object is not only present but also contains data. The current check for `null` and `undefined` is insufficient as an empty object `{}` can be stored. The logic should be updated to check if the object has any keys. This will ensure that refunds with empty but non-null banking snapshots are correctly identified as invalid. This change will be automatically picked up by the `approvePaymentFirstStage` action, preventing new invalid refunds from being approved.
Files: `lib/utils/payment-banking-validation.ts`

**Step 2: Filter Invalid Refunds from Banking Dashboard and NACHA Views**  
In the `getApprovedPayments` and `getPaymentsReadyForNacha` functions, update the Prisma query's `whereClause.NOT` condition. The current filter only excludes refunds where `bankingSnapshot` is `Prisma.DbNull`. This is insufficient to filter out records where the snapshot is an empty JSON object (`{}`). Modify the query to also exclude outgoing ACH refunds where the `bankingSnapshot` is present but effectively empty. This can be achieved by adding another condition to the `NOT` array that checks for the absence of a key that must exist in a valid snapshot, such as `bankName`. This will prevent existing and future invalid refund records from appearing on the Banking Dashboard and in the NACHA generation list.
Files: `lib/actions/payment-approvals.ts`

**Step 3: Verify UI Error Feedback on Payments Dashboard**  
This is a verification step with no expected code changes. Confirm that the existing error handling in the `handleApprove` function correctly displays a toast notification when the `approvePaymentFirstStage` server action returns an error. This ensures that when a user attempts to approve a refund with missing banking information, the strengthened server-side validation from Step 1 provides clear and immediate feedback to the user on the Payments Dashboard.
Files: `app/dashboard/payments/payments-client.tsx`

**Risk Level:** LOW — The changes are targeted at validation and data filtering logic. The primary risk is that the Prisma query modification to filter empty JSON objects might have unintended side effects on performance or other payment types, but this is unlikely as the change will be narrowly scoped to outgoing refunds. The client-side changes are minimal and confined to error handling that is already in place.

## Proposed Code Changes

### `lib/utils/payment-banking-validation.ts` (modify)
The original validation for `bankingSnapshot` only checked for `null` or `undefined`. This allowed refunds with an empty JSON object (`{}`) to pass validation, causing them to appear on the banking dashboard without data. This change strengthens the `hasSnapshot` check to ensure the `bankingSnapshot` is an object with at least one key, correctly identifying empty snapshots as invalid.
```typescript
--- a/lib/utils/payment-banking-validation.ts
+++ b/lib/utils/payment-banking-validation.ts
@@ -50,9 +50,11 @@
   const hasOutgoingBank = Boolean(
     payment.outgoingBankId || payment.outgoingBankAccount?.id
   );
-  const hasSnapshot =
-    payment.bankingSnapshot !== null &&
-    payment.bankingSnapshot !== undefined;
+  const hasSnapshot =
+    payment.bankingSnapshot !== null &&
+    payment.bankingSnapshot !== undefined &&
+    typeof payment.bankingSnapshot === "object" &&
+    Object.keys(payment.bankingSnapshot).length > 0;
 
   if (!hasOutgoingBank && !hasSnapshot) {
     return "Cannot approve refund for NACHA processing: missing ACH banking information (Bank Name, Routing #, Account #). The party must have banking details on file before this refund can be approved.";
```

### `lib/actions/payment-approvals.ts` (modify)
The database queries in `getApprovedPayments` and `getPaymentsReadyForNacha` were only filtering out refunds where the `bankingSnapshot` was `NULL`. This allowed records with an empty JSON object (`{}`) to be fetched and displayed. This change updates the Prisma query to exclude records where `bankingSnapshot` is either `NULL` or an empty object, ensuring that only refunds with valid banking information are shown on the banking dashboard and included in NACHA file generation.
```typescript
--- a/lib/actions/payment-approvals.ts
+++ b/lib/actions/payment-approvals.ts
@@ -942,8 +942,13 @@
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
@@ -1166,8 +1171,13 @@
               { type: { in: BANKING_REFUND_TYPES } },
               { paymentMethod: { not: "CHECK" } },
               { outgoingBankId: null },
-              { bankingSnapshot: { equals: Prisma.DbNull } },
+              {
+                OR: [
+                  { bankingSnapshot: { equals: Prisma.DbNull } },
+                  { bankingSnapshot: { equals: {} as Prisma.InputJsonValue } },
+                ],
+              },
             ],
           },
         ],
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Vitest`

- **shouldReturnTrueForValidAndPopulatedSnapshot** — Verifies that the utility correctly identifies a complete and valid banking snapshot object.
- **shouldReturnFalseForEmptyObjectSnapshot** *(edge case)* — This is the primary regression test for the bug fix, ensuring that an empty object is no longer considered a valid snapshot.
- **shouldReturnFalseForNullSnapshot** *(edge case)* — Ensures the validation correctly handles null inputs, which is a critical boundary condition.
- **shouldReturnFalseForUndefinedSnapshot** *(edge case)* — Ensures the validation correctly handles undefined inputs as another key boundary condition.
- **shouldFilterOutRecordsWithNullOrEmptySnapshotsAtDatabaseLevel** — Verifies that the data-fetching action correctly filters out invalid records at the database query level, preventing them from reaching the UI.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD establishes the core business rule that is at the heart of the ticket: no payment (including a refund) can be processed without a verified banking account explicitly tied to the receiving organization. It also specifies the data model, including a "banking_verified" flag, which is central to the required validation logic.

**Suggested Documentation Updates:**

- IDRE Worflow: The workflow should be updated to explicitly mention that refund approval is contingent on the recipient having verified banking information on file.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: The QA checklist for "Refunds & Financials" should be updated to include a negative test case verifying that refunds without banking information cannot be approved or appear on the Banking Dashboard.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._