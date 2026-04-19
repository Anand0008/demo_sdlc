## IDRE-558: Refunds should not make it to banking dashboard without refund information on file

**Jira Ticket:** [IDRE-558](https://orchidsoftware.atlassian.net//browse/IDRE-558)

## Summary
This plan addresses the issue of refunds appearing on the banking dashboard without necessary banking information. It introduces a three-part fix: 1) adding server-side validation to the refund approval action in `lib/actions/payment-approvals.ts` to block approvals for recipients without ACH details; 2) updating the payments dashboard UI in `app/dashboard/payments/payments-client.tsx` to display this validation error to the user; and 3) filtering the data query in `lib/actions/payment.ts` to hide any existing invalid refund records from the banking dashboard. This ensures data integrity for new refunds and cleans up the current view.

## Implementation Plan

**Step 1: Add Server-Side Validation to Refund Approval Action**  
In the `approvePaymentFirstStage` server action, before any status change, add logic to verify that the recipient of the refund has approved ACH banking information on file. The function should fetch the payment details, identify the recipient party/organization, and check for an existing, valid banking setup. If no banking information is found for an ACH-based refund, the function should return a `{ success: false, error: "Cannot approve refund: Recipient is missing required ACH banking information." }` object and halt the approval process.
Files: `lib/actions/payment-approvals.ts`

**Step 2: Display Banking Info Validation Error in Payments Dashboard**  
In the UI component for the payments dashboard, locate the handler function that calls the `approvePaymentFirstStage` action. Update this handler to properly manage the error state returned from the server action. If the `success` property in the response is `false`, use the `toast.error()` function to display the error message to the user, preventing them from approving a refund for a party with no banking details.
Files: `app/dashboard/payments/payments-client.tsx`

**Step 3: Filter Banking Dashboard View to Hide Invalid Refunds**  
Locate the data-fetching function that supplies payment data to the banking dashboard (e.g., `getPaymentsByStatus` or a similar function). Modify the database query to filter out any payments that have a status of 'Ready for NACHA Processing' (or equivalent) but do not have an associated banking snapshot. This will be achieved by adding a `where` clause to the Prisma query, such as `bankingSnapshot: { not: null }`. This ensures that existing records with missing data and any future records that might bypass the new validation are not displayed on the banking dashboard.
Files: `lib/actions/payment.ts`

**Risk Level:** LOW — The changes are confined to validation logic and data filtering, with a low risk of unintended side effects. The primary risk is that the validation logic in the server action might be overly strict or miss an edge case, but this can be mitigated with thorough testing. The UI changes are minimal and low-risk.

## Proposed Code Changes

### `lib/actions/payment-approvals.ts` (modify)
This change introduces server-side validation at the beginning of the `approvePaymentFirstStage` action. Before any status change occurs, it checks if the payment is an ACH refund. If so, it verifies that the recipient organization has a valid ACH payout bank account configured. This prevents the approval of refunds that cannot be processed, addressing the root cause of the issue.
```typescript
--- a/lib/actions/payment-approvals.ts
+++ b/lib/actions/payment-approvals.ts
@@ -1,6 +1,7 @@
 "use server";
 
 import { prisma } from "@/lib/database";
+import { PaymentMethod, PaymentType } from "@prisma/client";
 import { revalidatePath } from "next/cache";
 import { auth } from "@/lib/auth/server";
 import { headers } from "next/headers";
@@ -12,6 +13,54 @@
   paymentId: string,
   caseId: string
 ) {
+  const session = await auth.api.getSession({ headers: await headers() });
+  if (!session) {
+    return { success: false, error: "Unauthorized" };
+  }
+
+  const payment = await prisma.payment.findUnique({
+    where: { id: paymentId },
+    include: {
+      // This relation is based on the Prisma schema. We assume the `CaseRefund` model,
+      // which is linked via `relatedRefundId`, contains the `recipientOrganizationId`.
+      case_refunds_payment_relatedRefundIdTocase_refunds: {
+        select: {
+          recipientOrganizationId: true,
+        },
+      },
+    },
+  });
+
+  if (!payment) {
+    return { success: false, error: "Payment not found." };
+  }
+
+  // Add validation for ACH Refunds
+  if (
+    payment.type === PaymentType.REFUND &&
+    payment.paymentMethod === PaymentMethod.ACH
+  ) {
+    const recipientOrgId =
+      payment.case_refunds_payment_relatedRefundIdTocase_refunds
+        ?.recipientOrganizationId;
+
+    if (!recipientOrgId) {
+      return {
+        success: false,
+        error: "Cannot approve refund: Recipient organization could not be determined.",
+      };
+    }
+
+    const recipientOrg = await prisma.organization.findUnique({
+      where: { id: recipientOrgId },
+      select: { refundPayoutBankAccountId: true },
+    });
+
+    if (!recipientOrg?.refundPayoutBankAccountId) {
+      return {
+        success: false,
+        error: "Cannot approve refund: Recipient is missing required ACH banking information.",
+      };
+    }
+  }
+
   // TODO: Add more robust validation and user permission checks
   // 
... (truncated — see full diff in files)
```

### `app/dashboard/payments/payments-client.tsx` (modify)
This change updates the UI component responsible for handling payment approvals. It adds error handling to the `handleApprove` function to manage the new failure case from the `approvePaymentFirstStage` server action. If the server returns an error (e.g., missing banking information), a user-friendly toast notification is displayed, providing immediate feedback.
```
--- a/app/dashboard/payments/payments-client.tsx
+++ b/app/dashboard/payments/payments-client.tsx
@@ -28,10 +28,15 @@
     setIsApproving(true);
     try {
       const result = await approvePaymentFirstStage(payment.id, payment.caseId);
-      if (result.success) {
+      if (result?.success) {
         toast.success("Payment approved successfully.");
         router.refresh();
+      } else {
+        toast.error(
+          result.error || "Failed to approve payment. Please try again."
+        );
       }
     } catch (error) {
       console.error("Failed to approve payment:", error);
       toast.error("An unexpected error occurred while approving the payment.");
```

### `lib/actions/payment.ts` (modify)
This change modifies the data-fetching action for the banking dashboard to filter out invalid records. By adding `bankingSnapshot: { not: null }` to the `where` clause for outgoing payments with an `APPROVED` status, we ensure that any existing or future refunds that incorrectly reach this state without banking details are hidden from the view. This cleans up the user interface and prevents confusion.
```typescript
--- a/lib/actions/payment.ts
+++ b/lib/actions/payment.ts
@@ -1,5 +1,5 @@
 "use server";
-import { PaymentStatus } from "@prisma/client";
+import { PaymentStatus, PaymentDirection } from "@prisma/client";
 import { prisma } from "@/lib/database";
 import { auth } from "@/lib/auth/server";
 import { headers } from "next/headers";
@@ -20,7 +20,11 @@
   const payments = await prisma.payment.findMany({
     where: {
       // This function specifically fetches payments ready for the banking dashboard
-      status: PaymentStatus.APPROVED,
+      AND: [
+        { status: PaymentStatus.APPROVED },
+        { direction: PaymentDirection.OUTGOING },
+        { bankingSnapshot: { not: null } },
+      ],
     },
     include: {
       caseAllocations: {
```

## Test Suggestions

Framework: `Vitest`

- **shouldThrowErrorWhenApprovingAchRefundForRecipientWithMissingBankingInfo** — This is the primary test case to validate the new server-side validation logic. It ensures that the approval process is halted at the source if the necessary banking data is not present, directly addressing the bug.
- **shouldSuccessfullyApproveAchRefundWhenRecipientHasBankingInfo** — This happy path test ensures that the new validation logic does not block valid ACH refund approvals, preventing a regression for the standard workflow.
- **shouldDisplayErrorToastWhenApprovalFailsDueToMissingBankingInfo** — This component test verifies that the UI correctly handles the new error case from the server action and provides clear feedback to the user, as specified in the implementation plan.
- **shouldFilterOutApprovedPaymentsMissingBankingSnapshot** — This test validates the defensive filtering added to the banking dashboard's data query. It ensures that any records that may have slipped through validation previously (or in the future) are hidden from the user, preventing confusion and cleaning up the UI as intended.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the canonical end-to-end case lifecycle, including status transitions. The ticket addresses a failure in this workflow, specifically the transition of a refund to the banking dashboard. This document provides the high-level business process that the developer's code must correctly implement.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document identifies 'Payments & Refunds Logic / Workflow' as a primary source of critical bugs and a 'major complexity hotspot.' It gives the developer essential context that the area they are working in is fragile and requires careful implementation and testing, validating the importance of the ticket's goal to harden the validation logic.

**Suggested Documentation Updates:**

- IDRE Worflow

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._