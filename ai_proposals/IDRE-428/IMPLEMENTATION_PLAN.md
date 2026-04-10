## IDRE-428: IDRE Payouts should be in hold until both parties have paid

**Jira Ticket:** [IDRE-428](https://orchidsoftware.atlassian.net//browse/IDRE-428)

## Summary
Update IDRE payout creation to set the status to 'Hold' if either party has an outstanding balance. Add an event listener to automatically release these holds when full payment is received, and ensure held payouts are hidden from the Banking Dashboard.

## Implementation Plan

**Step 1: Set Initial Payout Status to Hold Based on Balances**  
Modify the payout creation logic for internal distributions (Capitol Bridge, VeraTru, Halo). When creating these payouts, check the IP and NIP balances (using the existing auto-approval check or similar logic). If either party has a balance greater than zero (not paid in full), set the initial status of the created payout to `HOLD` instead of `PENDING` or `APPROVED`.
Files: `lib/services/refund-service.ts`

**Step 2: Automatically Release Held Payouts on Full Payment**  
Create a function in `refund-service.ts` (e.g., `releaseHeldPayouts`) that checks a case's held payouts and updates their status to `PENDING` or `APPROVED` (ready for the Banking Dashboard) if both IP and NIP are now paid in full. Call this function from the payment completion event handler (e.g., in `case-subscriber.ts` listening to payment status changes or directly in the Stripe webhook handler) whenever a payment successfully completes.
Files: `lib/events/subscribers/case-subscriber.ts`, `lib/services/refund-service.ts`

**Step 3: Hide Held Payouts from Banking Dashboard**  
Ensure the Banking Dashboard queries or filters explicitly exclude payouts with a `HOLD` status from the list of payouts ready for finalization, so they do not appear until their status is updated.
Files: `app/dashboard/payments/payments-client.tsx`

**Risk Level:** MEDIUM — Modifying payout statuses and the conditions for their release involves financial workflows. Incorrect logic could lead to payouts being held indefinitely or released prematurely.

## Proposed Code Changes

### `lib/services/refund-service.ts` (modify)
Sets the initial status of internal distributions to `HOLD` if the auto-approval check fails (meaning balances are not paid in full). Adds a new function `releaseHeldPayouts` to check and release these holds once full payment is confirmed.
```typescript
@@ -... +... @@
-    const initialStatus = autoApprovalCheck.canAutoApprove 
-      ? PaymentStatus.APPROVED 
-      : PaymentStatus.PENDING;
+    const initialStatus = autoApprovalCheck.canAutoApprove 
+      ? PaymentStatus.APPROVED 
+      : PaymentStatus.HOLD;
@@ -... +... @@
+/**
+ * Checks if a case has any held internal distributions and releases them
+ * if both parties have paid in full.
+ */
+export async function releaseHeldPayouts(caseId: string) {
+  const autoApprovalCheck = await checkInternalDistributionAutoApproval(caseId);
+  
+  // If balances are not paid in full, we cannot release the holds
+  if (!autoApprovalCheck.canAutoApprove) {
+    return { success: false, reason: "Balances not paid in full" };
+  }
+
+  // Find held payouts for this case
+  const heldPayouts = await prisma.payment.findMany({
+    where: {
+      caseId,
+      status: "HOLD",
+      direction: "OUTBOUND",
+    }
+  });
+
+  if (heldPayouts.length === 0) {
+    return { success: true, releasedCount: 0 };
+  }
+
+  // Update them to APPROVED so they appear on the Banking Dashboard
+  await prisma.payment.updateMany({
+    where: {
+      id: { in: heldPayouts.map(p => p.id) }
+    },
+    data: {
+      status: "APPROVED"
+    }
+  });
+
+  return { success: true, releasedCount: heldPayouts.length };
+}
```

### `lib/events/subscribers/case-subscriber.ts` (modify)
Triggers the release of held payouts whenever a payment is completed, ensuring that payouts automatically move to the Banking Dashboard once both parties have paid in full.
```typescript
@@ -... +... @@
 import { prisma } from "@/lib/database";
+import { releaseHeldPayouts } from "@/lib/services/refund-service";
 
@@ -... +... @@
 export async function handlePaymentCompleted(event: PaymentCompletedEvent) {
   // Existing payment completion logic...
   
+  // Check and release any held payouts if both parties are now paid in full
+  try {
+    await releaseHeldPayouts(event.caseId);
+  } catch (error) {
+    console.error(`Failed to release held payouts for case ${event.caseId}:`, error);
+  }
 }
```

### `app/dashboard/payments/payments-client.tsx` (modify)
Explicitly filters out any payouts with a `HOLD` status from the Banking Dashboard so they cannot be finalized prematurely.
```
@@ -... +... @@
   const filteredPayments = useMemo(() => {
     return payments.filter((payment) => {
+      // Hide held payouts from the Banking Dashboard
+      if (payment.status === 'HOLD') {
+        return false;
+      }
       // Existing filter logic...
       return true;
     });
   }, [payments, /* other dependencies */]);
```

## Test Suggestions

Framework: `Jest / React Testing Library`

- **shouldCreatePayoutWithHoldStatusWhenBalancesOutstanding** — Verifies that a new IDRE payout is automatically placed on hold if both parties have not paid in full.
- **shouldNotReleaseHeldPayoutsWhenPartialPaymentLeavesBalance** *(edge case)* — Verifies that a partial payment does not prematurely release the hold on an IDRE payout.
- **shouldReleaseHeldPayoutsWhenAllPartiesPaidInFull** — Verifies that held payouts are released when both parties are paid in full.
- **shouldTriggerReleaseHeldPayoutsOnPaymentCompletedEvent** — Verifies that the case subscriber listens to payment completions and triggers the release check.
- **shouldFilterOutHoldPayoutsFromBankingDashboard** — Verifies that payouts in HOLD status are hidden from the Banking Dashboard.

## AI Confidence Scores
Plan: 85%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._