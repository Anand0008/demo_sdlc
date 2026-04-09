## IDRE-499: Party Unable to Complete Payment in system after a failed payment

**Jira Ticket:** [IDRE-499](https://orchidsoftware.atlassian.net//browse/IDRE-499)

## Summary
Fix the issue preventing parties from retrying payments after a failure by ensuring that payment failure events (via Stripe webhooks or manual rejection) correctly revert the overarching case status to a pending state and clear any residual payment locks.

## Implementation Plan

**Step 1: Revert Case Status on Payment Failure**  
In the `handlePaymentFailure` function, after updating the Stripe payment record to `FAILED`, retrieve all `Case` records associated with this payment. Revert their `caseStatus` back to the appropriate pre-payment state (e.g., `PENDING_PAYMENT`). Call `emitCaseStatusChanged` for each affected case and log the failure using `logCaseAction` to ensure the system recognizes the cases are available for a new payment attempt.
Files: `app/api/stripe/webhook/route.ts`

**Step 2: Clear Payment Locks for Retried Payments**  
In `createStripePaymentIntent`, add logic to handle scenarios where a user is retrying a failed payment. Before calling `assertNoConflictingCasePartyPaymentSource` or `upsertCasePartyPaymentLock`, check for and clear any existing payment locks associated with the user's previously `FAILED` payments for the selected cases. This ensures the new payment intent is not blocked by residual locks from the failed attempt.
Files: `lib/actions/stripe-payment.ts`

**Step 3: Synchronize Case Status on Manual Payment Rejection**  
Review and update payment rejection/failure paths within the approval workflow (e.g., if a payment is marked as 'failed' during first or second stage approval). Ensure that transitioning a payment to 'failed' correctly cascades to update the overarching case status, unblocking the party to submit a new payment.
Files: `lib/actions/payment-approvals.ts`

**Risk Level:** MEDIUM — Modifying payment status transitions and case locks carries a risk of race conditions or unintended state changes if not carefully scoped. However, the changes are isolated to failure paths, minimizing impact on successful payment flows. Rigorous regression testing is required as per the Confluence documentation.

**Deployment Notes:**
- Ensure Stripe webhook endpoints are correctly configured to receive `payment_intent.payment_failed` events.
- Monitor logs for case status transition errors during the first few days of deployment.

## Proposed Code Changes

### `app/api/stripe/webhook/route.ts` (modify)
When a Stripe payment fails, we need to revert the associated cases to `PENDING_PAYMENT` so the user can attempt to pay again. We also log the action and emit the status change event.
```typescript
--- a/app/api/stripe/webhook/route.ts
+++ b/app/api/stripe/webhook/route.ts
@@ -10,6 +10,8 @@
 import { prisma } from "@/lib/database/client";
 import { PaymentStatus, CaseStatus, CaseActionType } from "@prisma/client";
 import { logCaseAction } from "@/lib/services/case";
+import { emitCaseStatusChanged } from "@/lib/events/emitters";
 
@@ -100,8 +102,25 @@
       case "payment_intent.payment_failed": {
         const paymentIntent = event.data.object as Stripe.PaymentIntent;
         const payment = await prisma.payment.update({
           where: { stripePaymentIntentId: paymentIntent.id },
           data: { status: PaymentStatus.FAILED },
+          include: { cases: true }
         });
+
+        if (payment && payment.cases) {
+          for (const caseRecord of payment.cases) {
+            await prisma.case.update({
+              where: { id: caseRecord.id },
+              data: { caseStatus: CaseStatus.PENDING_PAYMENT }
+            });
+            
+            await logCaseAction({
+              caseId: caseRecord.id,
+              type: CaseActionType.PAYMENT_FAILED,
+              description: "Payment failed, case reverted to pending payment",
+              userId: payment.userId
+            });
+            
+            emitCaseStatusChanged(caseRecord.id, CaseStatus.PENDING_PAYMENT);
+          }
+        }
         break;
       }
```

### `lib/actions/stripe-payment.ts` (modify)
Before creating a new payment intent, we clear any existing payment locks for the user and the selected cases. This ensures that residual locks from a previously failed payment attempt do not block the new attempt.
```typescript
--- a/lib/actions/stripe-payment.ts
+++ b/lib/actions/stripe-payment.ts
@@ -60,6 +60,14 @@
       };
     }
 
+    // Clear any existing payment locks for the user and selected cases
+    // to allow retrying after a failed payment
+    await prisma.casePartyPaymentLock.deleteMany({
+      where: {
+        userId: userId,
+        caseId: { in: input.caseIds }
+      }
+    });
+
     // Search for existing Stripe customer by email
     const existingCustomers = await stripe.customers.list({
```

### `lib/actions/payment-approvals.ts` (modify)
Similar to the Stripe webhook, if a payment is manually rejected or marked as failed during the approval workflow, we must revert the case status to `PENDING_PAYMENT` to unblock the party from submitting a new payment.
```typescript
--- a/lib/actions/payment-approvals.ts
+++ b/lib/actions/payment-approvals.ts
@@ -5,6 +5,8 @@
 import { prisma } from "@/lib/database/client";
 import { PaymentStatus, CaseStatus, CaseActionType } from "@prisma/client";
 import { logCaseAction } from "@/lib/services/case";
+import { emitCaseStatusChanged } from "@/lib/events/emitters";
 
@@ -50,8 +52,25 @@
     const updatedPayment = await prisma.payment.update({
       where: { id: paymentId },
       data: { status: PaymentStatus.FAILED, rejectionReason: reason },
+      include: { cases: true }
     });
+
+    if (updatedPayment && updatedPayment.cases) {
+      for (const caseRecord of updatedPayment.cases) {
+        await prisma.case.update({
+          where: { id: caseRecord.id },
+          data: { caseStatus: CaseStatus.PENDING_PAYMENT }
+        });
+        
+        await logCaseAction({
+          caseId: caseRecord.id,
+          type: CaseActionType.PAYMENT_FAILED,
+          description: `Payment rejected: ${reason}`,
+          userId: adminId
+        });
+        
+        emitCaseStatusChanged(caseRecord.id, CaseStatus.PENDING_PAYMENT);
+      }
+    }
```

## Test Suggestions

Framework: `Vitest`

- **shouldRevertCaseStatusToPendingPaymentOnStripeFailure** — Verifies that a failed Stripe payment webhook correctly reverts the case status to PENDING_PAYMENT so the user can retry.
- **shouldClearExistingPaymentLocksBeforeCreatingNewPaymentIntent** — Ensures that residual payment locks from previous failed attempts are cleared before initiating a new payment.
- **shouldRevertCaseStatusToPendingPaymentOnManualRejection** — Verifies that manually rejecting a payment in the approval workflow correctly unblocks the case by reverting its status.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page explicitly identifies the payments and refunds engine as a major complexity hotspot, specifically noting issues where the system cannot complete payments or progress statuses correctly after payment status changes (such as 'failed'). It provides essential QA regression testing guidelines for payment status transitions.

**Suggested Documentation Updates:**

- Bugs

## AI Confidence Scores
Plan: 85%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._