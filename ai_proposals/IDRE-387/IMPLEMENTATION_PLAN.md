## IDRE-387: Add overage funds and create refunds on accounts even after a payment is applied

**Jira Ticket:** [IDRE-387](https://orchidsoftware.atlassian.net//browse/IDRE-387)

## Summary
Update the case payment ledger and backend payment actions to allow recording overage funds and issuing refunds on fully paid cases, ensuring these actions bypass automatic status transitions and respect banking status rules for refunds.

## Implementation Plan

**Step 1: Enable overage funds and refunds in the ledger UI**  
Update the UI to remove disabled states and validation checks that prevent users from recording payments or adding funds when a case is already paid in full. Ensure the UI allows initiating a refund for overage amounts without throwing validation errors for exceeding the expected balance.
Files: `components/case-payment-ledger-v2.tsx`

**Step 2: Support overage payments without status transitions**  
Modify the payment recording action (e.g., `recordOverageFunds` or the manual payment handler) to accept payments on fully paid cases. Add conditional logic to explicitly bypass automatic case, payment, and refund status transitions when recording these additional overage funds.
Files: `lib/actions/payment.ts`

**Step 3: Implement banking status checks for overage refunds**  
Update the refund creation logic (e.g., `createObligationRefund`) to handle overage refunds. Integrate the existing banking verification checks to evaluate the party's bank account status. Set the newly created refund's status to `PENDING` if banking is pending, and `HELD` if banking is missing, adhering to the standard refund workflow.
Files: `lib/actions/payment.ts`

**Risk Level:** MEDIUM — Modifying payment and refund logic carries inherent financial risk. Bypassing case status transitions requires careful conditional logic to ensure normal payments still trigger the correct status updates, while overage payments do not.

**Deployment Notes:**
- Ensure QA performs regression testing on standard payment flows to verify that normal case status transitions are not inadvertently bypassed.

## Proposed Code Changes

### `components/case-payment-ledger-v2.tsx` (modify)
Removed UI validation checks and disabled states that prevented users from recording payments or adding funds when a case is already paid in full. Also removed the validation that prevented initiating refunds for overage amounts.
```
@@ -150,8 +150,8 @@
   const handleRecordPayment = async () => {
     // ... existing logic ...
 
-    if (receivedAmount > expectedAmount) {
-      toast.error("Cannot receive more than expected amount.");
-      return;
-    }
+    // IDRE-387: Allow overage payments
+    // Removed validation that prevents receiving more than expected amount
 
     try {
@@ -250,8 +250,8 @@
   const handleCreateRefund = async () => {
     // ... existing logic ...
 
-    if (refundAmount > availableBalance) {
-      toast.error("Refund amount cannot exceed available balance.");
-      return;
-    }
+    // IDRE-387: Allow refunds for overage amounts
+    // Removed validation that prevents refunding more than the expected balance
 
     try {
@@ -350,7 +350,7 @@
         <Button
           variant="outline"
           size="sm"
-          disabled={party.balance <= 0}
+          disabled={false} // IDRE-387: Allow adding funds even after a case has been paid in full
           onClick={() => openManualPayment(party)}
         >
           Record Payment
```

### `lib/actions/payment.ts` (modify)
Updated backend actions to accept payments on fully paid cases, bypass automatic status transitions for overage funds, and apply banking status checks to determine the correct refund status (`PENDING` or `HELD`) based on the party's bank account status.
```typescript
@@ -100,12 +100,15 @@
 export async function recordOverageFunds(params: RecordOverageParams) {
   // ... existing setup ...
 
-  if (caseRecord.status === 'PAID') {
-    throw new Error("Cannot add funds to a fully paid case.");
-  }
+  // IDRE-387: Allow adding funds even after a case has been paid in full
+  // Removed check that throws error if case is PAID
 
   const payment = await prisma.payment.create({
     data: {
       // ... existing data ...
     }
   });
 
-  await updateCaseStatus(caseRecord.id);
+  // IDRE-387: Explicitly bypass automatic case, payment, and refund status transitions
+  // when recording these additional overage funds.
+  // Removed automatic status transition calls here.
 
   return payment;
 }
@@ -200,6 +203,20 @@
 export async function createObligationRefund(params: CreateRefundParams) {
   // ... existing setup ...
 
+  // IDRE-387: Implement banking status checks for overage refunds
+  const party = await prisma.caseParty.findUnique({
+    where: { id: params.partyId },
+    include: { bankAccounts: true }
+  });
+
+  let refundStatus = 'PENDING';
+  const hasApprovedBank = party?.bankAccounts?.some(b => b.status === 'APPROVED');
+  const hasPendingBank = party?.bankAccounts?.some(b => b.status === 'PENDING');
+
+  if (!hasApprovedBank && !hasPendingBank) {
+    refundStatus = 'HELD';
+  } else if (hasPendingBank && !hasApprovedBank) {
+    refundStatus = 'PENDING';
+  }
+
   const refund = await prisma.caseRefund.create({
     data: {
       // ... existing data ...
-      status: 'PENDING',
+      status: refundStatus,
     }
   });
```

## Test Suggestions

Framework: `Vitest / React Testing Library`

- **shouldRenderAddFundsButtonEnabledWhenCaseIsFullyPaid** — Verifies that the UI allows users to add funds even when the case is already fully paid.
- **shouldAllowInitiatingRefundForOverageAmount** — Verifies that the UI allows initiating a refund for overage amounts on a fully paid case.
- **shouldProcessOverageFundsWithoutChangingCaseStatus** — Verifies that backend actions accept payments on fully paid cases without altering the case status.
- **shouldCreatePendingRefundWhenBankingDetailsExist** — Verifies that refunds are created with a 'PENDING' status when the party has banking details.
- **shouldCreateHeldRefundWhenNoBankingDetailsExist** *(edge case)* — Verifies that refunds are created with a 'HELD' status when the party lacks banking details.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — Highlights that payment and refund events currently trigger case status transitions, which is a critical constraint since the ticket requires overage funds NOT to change the case status.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Documents the end-to-end case lifecycle and payment collection, which will be impacted by the new ability to process overages and refunds after a case is paid in full.

**Suggested Documentation Updates:**

- IDRE Worflow: Needs to be updated to document the new process for handling overpayments and refunds after a case is paid in full, clarifying that these actions do not affect the case status.
- Bugs: The QA test matrices mentioned for "Case status transitions on payment/refund events" should be updated to cover overpayments and post-closure refunds to ensure statuses do not change.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._