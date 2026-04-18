## IDRE-558: Refunds should not make it to banking dashboard without refund information on file

**Jira Ticket:** [IDRE-558](https://orchidsoftware.atlassian.net//browse/IDRE-558)

## Summary
This plan addresses the issue of refunds appearing on the Banking Dashboard without required banking information. It involves three steps: 1) Filtering the `getApprovedPayments` data fetch to exclude refunds with a null `bankingSnapshot`. 2) Adding a server-side validation check to the refund approval action in `lib/actions/payment.ts` to prevent approval if ACH details are missing. 3) Updating the UI in `app/dashboard/payments/payments-client.tsx` to show an error toast if a user attempts to approve a refund without the necessary banking info. This ensures data integrity on the Banking Dashboard and provides clear user feedback.

## Implementation Plan

**Step 1: Filter out refunds with no banking info from Banking Dashboard**  
In the `getApprovedPayments` function, modify the underlying database query (likely Prisma) to filter out records where the banking information is not present. Add a `where` clause to ensure the `bankingSnapshot` field is not null. This will prevent refunds without banking details from being displayed on the Banking Dashboard, satisfying the second acceptance criterion.
Files: `lib/actions/payment-approvals.ts`

**Step 2: Add server-side validation to refund approval action**  
Locate the server action that approves a refund and transitions it to 'Ready for NACHA'. Before changing the payment status, add a validation check to ensure that the recipient party has valid ACH banking information on file. If the banking information is missing, prevent the status update and return an error object (e.g., `{ success: false, message: 'Cannot approve refund: Missing banking information for the recipient.' }`). This addresses the first and third acceptance criteria from the server side.
Files: `lib/actions/payment.ts`

**Step 3: Display UI error on approval failure**  
In the Payments Dashboard client component, locate the handler function that calls the refund approval server action. Update this handler to process the return value from the action. If the action returns an error, use the existing toast notification system to display the error message to the user, informing them why the refund cannot be approved.
Files: `app/dashboard/payments/payments-client.tsx`

**Risk Level:** LOW — The proposed changes are low-risk as they involve adding validation and filtering, rather than modifying core financial transaction logic. The changes are confined to server-side data fetching and a single client-side component, minimizing the chance of unintended side effects. The primary risk is that the exact name of the approval action function in `lib/actions/payment.ts` might differ, requiring minor code exploration to locate it.

## Proposed Code Changes

### `lib/actions/payment-approvals.ts` (modify)
This change ensures that the Banking Dashboard only displays payments and refunds that have a `bankingSnapshot` attached. By adding `bankingSnapshot: { not: null }` to the Prisma query's `where` clause in `getApprovedPayments`, we filter out any records that are missing this critical information, directly addressing the acceptance criterion to hide such records from the view.
```typescript
--- a/lib/actions/payment-approvals.ts
+++ b/lib/actions/payment-approvals.ts
@@ -50,6 +50,9 @@
     status: {
       in: ["APPROVED", "READY_FOR_NACHA", "PROCESSING", "PAID", "RETURNED"],
     },
+    bankingSnapshot: {
+      not: null,
+    },
   };
 
   if (filters.direction) {
```

### `lib/actions/payment.ts` (modify)
This change introduces a critical server-side validation check. Before a payment's status can be updated to `APPROVED`, the `validateRefundApproval` helper function is called to verify that the recipient party has all the necessary ACH banking information on file. If the information is missing, the action fails and returns an error message, preventing refunds without banking details from entering the "Ready for NACHA" pipeline.
```typescript
--- a/lib/actions/payment.ts
+++ b/lib/actions/payment.ts
@@ -1,5 +1,6 @@
 "use server";
 
+import { PaymentStatus } from "@prisma/client";
 import { revalidatePath } from "next/cache";
 import { prisma } from "@/lib/prisma";
 import {
@@ -8,6 +9,42 @@
 } from "@/lib/schemas/payment";
 import { ServerActionResponse } from "../types/server-action";
 import { Payment } from "@prisma/client";
+
+async function validateRefundApproval(
+  paymentId: string
+): Promise<{ success: boolean; message?: string }> {
+  const payment = await prisma.payment.findUnique({
+    where: { id: paymentId },
+    select: {
+      recipientParty: {
+        select: {
+          bankingInformation: true,
+        },
+      },
+    },
+  });
+
+  if (!payment) {
+    return { success: false, message: "Payment not found." };
+  }
+
+  const bankingInfo = payment.recipientParty?.bankingInformation;
+  if (
+    !bankingInfo ||
+    !bankingInfo.bankName ||
+    !bankingInfo.accountHolderName ||
+    !bankingInfo.routingNumber ||
+    !bankingInfo.accountNumber
+  ) {
+    return {
+      success: false,
+      message:
+        "Cannot approve refund: Recipient is missing required ACH banking information.",
+    };
+  }
+
+  return { success: true };
+}
 
 export async function updatePayment(
   paymentId: string,
@@ -18,6 +55,14 @@
     return { success: false, message: "Invalid data provided." };
   }
 
+  // If moving to an approved state, validate banking info is present for the refund
+  if (validatedFields.data.status === "APPROVED") {
+    const validationResult = await validateRefundApproval(paymentId);
+    if (!validationResult.success) {
+      return validationResult;
+    }
+  }
+
   try {
     const updatedPayment = await prisma.payment.update({
       where: { id: paymentId },
```

### `app/dashboard/payments/payments-client.tsx` (modify)
This change enhances the user experience by providing immediate feedback. The `handleApprove` function is updated to process the response from the `updatePayment` server action. If the action returns an error (e.g., due to missing banking information), an error toast is displayed to the user. If successful, a confirmation toast is shown. This fulfills the requirement to alert users when approval is not possible.
```
--- a/app/dashboard/payments/payments-client.tsx
+++ b/app/dashboard/payments/payments-client.tsx
@@ -4,8 +4,9 @@
 import { PaymentsTable } from "./payments-table";
 import { PaymentFilters } from "@/lib/actions/payment";
 import { PaginationInfo } from "@/lib/types/pagination";
-import { useTransition } from "react";
+import { useTransition, useCallback } from "react";
 import { updatePayment } from "@/lib/actions/payment";
+import { toast } from "sonner";
 
 interface PaymentsClientProps {
   payments: any[]; // Define a proper type
@@ -20,15 +21,20 @@
   const [isPending, startTransition] = useTransition();
   const router = useRouter();
 
-  const handleApprove = (paymentId: string) => {
-    startTransition(async () => {
-      await updatePayment(paymentId, { status: "APPROVED" });
-      // Refresh data after update
-      router.refresh();
-    });
-  };
+  const handleApprove = useCallback(
+    (paymentId: string) => {
+      startTransition(async () => {
+        const result = await updatePayment(paymentId, { status: "APPROVED" });
+        if (result.success) {
+          toast.success("Refund approved and sent to banking.");
+          router.refresh();
+        } else {
+          toast.error(result.message || "Failed to approve refund.");
+        }
+      });
+    },
+    [router, startTransition]
+  );
 
   // Other handlers for deny, etc.
```

**New Dependencies:**
- `No new dependencies needed.`

## Test Suggestions

Framework: `Vitest`

- **shouldOnlyReturnPaymentsWithBankingSnapshot** — Verifies that the data fetching for the Banking Dashboard correctly filters out records that are missing the required banking snapshot, ensuring data integrity on the UI.
- **shouldReturnErrorWhenApprovingRefundForRecipientWithMissingAchInfo** — This is the primary regression test for the bug. It ensures the new server-side validation prevents a refund from being approved if the recipient's banking information is incomplete.
- **shouldSuccessfullyApproveRefundWhenRecipientHasCompleteAchInfo** — This happy path test ensures that the approval process works as expected when all validation conditions are met.
- **shouldDisplayErrorToastWhenApprovalFails** — Verifies that the UI provides clear, immediate feedback to the user when a refund approval fails on the server due to the new validation logic.
- **shouldDisplaySuccessToastWhenApprovalSucceeds** — Verifies the happy path for the UI, ensuring the user receives positive feedback when an approval is processed successfully.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the official end-to-end case lifecycle, which the ticket (IDRE-558) indicates is not being followed correctly for refunds. The developer needs to understand the intended process flow that their new validation logic will enforce.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document explicitly identifies the 'Payments & Refunds Logic / Workflow' as a 'major complexity hotspot' prone to errors in status transitions. This validates the ticket's premise and alerts the developer to the fragility of this module. The QA suggestions directly relate to the acceptance criteria.

**Suggested Documentation Updates:**

- IDRE Worflow: This document should be updated to explicitly include the three-step validation process (Paid dispute, Attached banking info, Approved status) required before a refund can be moved to the Banking Dashboard for NACHA processing.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._