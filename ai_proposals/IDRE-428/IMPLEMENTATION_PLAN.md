## IDRE-428: IDRE Payouts should be in hold until both parties have paid

**Jira Ticket:** [IDRE-428](https://orchidsoftware.atlassian.net//browse/IDRE-428)

## Summary
The implementation plan addresses the need to ensure IDRE payouts are held until both parties have paid in full. The core logic for this functionality already exists within `lib/services/refund-service.ts` and is triggered by `lib/events/subscribers/payment-subscriber.ts`. This plan focuses on adding comprehensive unit tests to `tests/services/refund-service.test.ts` to verify and solidify the existing behavior, ensuring payouts are correctly created with an `ON_HOLD` status and are automatically released to `APPROVED` status upon full payment from both parties. This approach validates the implementation without altering production code.

## Implementation Plan

**Step 1: Verify 'ON_HOLD' Payout Creation Logic**  
In `ensureInternalRefundDistributions`, the logic to set payment status to `ON_HOLD` already exists. This step is to confirm the logic at line 1176 (`const paymentStatus = autoApprovalCheck.canAutoApprove ? "APPROVED" : "ON_HOLD";`) correctly implements the hold requirement based on the result of `canAutoApproveDistributions`. No code change is expected, only verification.
Files: `lib/services/refund-service.ts`

**Step 2: Verify Automatic Payout Release Trigger**  
In `handlePaymentStatusChanged`, locate the block starting around line 307 that handles incoming `CASE_PAYMENT` status changes. Verify that the call to `releaseHeldInternalDistributions(allocation.case.id)` is correctly placed to trigger when a payment is `APPROVED` or `COMPLETED`. This confirms the automatic release mechanism. No code change is expected, only verification.
Files: `lib/events/subscribers/payment-subscriber.ts`

**Step 3: Add Test for Automatic Release of Held Payouts**  
Add a new `describe` block for `releaseHeldInternalDistributions`. Create a test case that simulates a scenario where `canAutoApproveDistributions` returns `true` for a case with existing `ON_HOLD` internal distribution payments. Mock `prisma.payment.findMany` to return these held payments. Assert that `prisma.payment.update` is called to change the status of these payments to `APPROVED` and set `includeOnNacha` to `true`. Also, assert that `prisma.paymentApproval.create` is called to log the automatic release.
Files: `tests/services/refund-service.test.ts`

**Step 4: Add Test for Payout Creation with 'ON_HOLD' Status**  
Add a new test case within the `describe` block for `ensureInternalRefundDistributions`. This test should simulate a scenario where `canAutoApproveDistributions` returns `false` (i.e., one or both parties have not paid in full). Assert that the calls to `prisma.payment.upsert` or `prisma.payment.create` for the internal distributions (Halo, VeraTru, Capitol Bridge) are made with `status: PaymentStatus.ON_HOLD`.
Files: `tests/services/refund-service.test.ts`

**Risk Level:** LOW — The core logic to implement the requested feature already exists in the codebase. The implementation plan focuses on adding test coverage to verify and formalize this existing behavior, which carries a very low risk of introducing regressions. No production code is being modified.

## Proposed Code Changes

### `tests/services/refund-service.test.ts` (modify)
This change adds four new unit tests to `tests/services/refund-service.test.ts` to cover the acceptance criteria of ticket IDRE-428.
1.  Two tests are added to the `ensureInternalRefundDistributions` suite to verify that IDRE payouts are correctly created with `ON_HOLD` status when party payments are incomplete, and with `APPROVED` status when payments are complete.
2.  A new test suite for `releaseHeldInternalDistributions` is added with three tests. These verify that held payouts are correctly released to `APPROVED` status when payment conditions are met, that they remain held if conditions are not met, and that the function handles cases with no held payments gracefully.
```typescript
--- a/tests/services/refund-service.test.ts
+++ b/tests/services/refund-service.test.ts
@@ -271,6 +271,88 @@
         })
       );
     });
+
+    it("should create internal distributions with ON_HOLD status when parties have not paid in full", async () => {
+      // Mock canAutoApproveDistributions to return false by providing incomplete payments
+      mockCaseFindUnique.mockResolvedValue({
+        id: "case-1",
+        typeOfDispute: "SINGLE",
+        DisputeLineItems: [{ id: "li-1", status: "ACTIVE" }],
+        paymentAllocations: [
+          {
+            partyType: "INITIATING",
+            allocatedAmount: 355,
+            payment: { status: "APPROVED", type: "CASE_PAYMENT", direction: "INCOMING" },
+          },
+          // NIP has not paid
+        ],
+      });
+
+      // No existing payments
+      mockPaymentFindUnique.mockResolvedValue(null);
+      mockPaymentFindFirst.mockResolvedValue(null);
+      mockPaymentUpsert.mockImplementation((args) => Promise.resolve({ id: "new-payment-id", ...args.create }));
+
+      const { ensureInternalRefundDistributions } = await import("@/lib/services/refund-service");
+      await ensureInternalRefundDistributions({ caseId: "case-1", caseType: "SINGLE", lineItemCount: 1 });
+
+      // Expect 3 distributions (Halo, CB, VeraTru)
+      expect(mockPaymentUpsert).toHaveBeenCalledTimes(3);
+
+      // Check that payments are created with ON_HOLD status and not for NACHA
+      expect(mockPaymentUpsert).toHaveBeenCalledWith(expect.objectContaining({
+        create: expect.objectContaining({
+          status: "ON_HOLD",
+          includeOnNacha: false,
+        }),
+      }));
+
+      // No approval record should be created for ON_HOLD payments
+      expect(mockPaymentApprovalCreate).not.toHaveBeenCalled();
+    });
+
+    it("should create internal distributions with APPROVED status when both parties have paid in full", async () => {
+      // Mock canAutoApproveDistributions to return true by providing
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Jest`

- **shouldCreatePayoutWithOnHoldStatusWhenEitherPartyHasAnOutstandingBalance** — Verifies that if a new IDRE payout is created for a specified client and payments are not complete, its status is correctly set to ON_HOLD. This covers Acceptance Criteria 1.
- **shouldCreatePayoutWithApprovedStatusWhenBothPartiesHavePaidInFull** — Verifies the happy path where both parties have paid in full upon creation, ensuring the payout is immediately approved and not put on hold.
- **shouldReleaseOnHoldPayoutToApprovedWhenFinalPaymentIsMade** — Verifies that when the final payment is made, a previously held payout is automatically released and moved to an approved state. This covers Acceptance Criteria 3.
- **shouldKeepPayoutOnHoldWhenPartialPaymentIsMadeButBalanceRemains** — Verifies that a held payout remains on hold if a payment event occurs but does not clear the outstanding balances for both parties. This covers Acceptance Criteria 2.
- **shouldDoNothingWhenNoHeldPayoutsAreFoundForTransaction** *(edge case)* — Verifies that the function handles the scenario where there are no held payouts to process, ensuring it doesn't crash or perform unnecessary actions.
- **shouldNotApplyHoldLogicForNonSpecifiedClients** *(edge case)* — This edge case test ensures the hold logic is only applied to the specific clients mentioned in the requirements and does not incorrectly hold payouts for other clients.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This document defines the core entities involved in the ticket: the Initiating Party (IP) and Non-Initiating Party (NIP). It clarifies their roles and the business rule that payments and banking are tied to these specific actor types, which is fundamental to understanding the ticket's requirements.
- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This page is relevant because it lists ticket IDRE-710, "Admin closure: status changes incorrectly when only IP/NIP paid". This is directly related to the logic required for IDRE-428, as both tickets concern system behavior based on the payment status of both parties. The developer should be aware of this concurrent work to avoid conflicts.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page outlines the end-to-end case lifecycle. The developer needs to understand this workflow to correctly place the new 'Hold' status for payouts, which will likely occur between the 'Arbitration' and 'Closure' phases, acting as a gate before the payout appears on the Banking Dashboard.

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