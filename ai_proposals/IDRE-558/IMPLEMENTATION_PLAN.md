## IDRE-558: Refunds should not make it to banking dashboard without refund information on file

**Jira Ticket:** [IDRE-558](https://orchidsoftware.atlassian.net//browse/IDRE-558)

## Summary
This plan addresses the issue of refunds appearing on the Banking Dashboard without necessary banking information. It involves three steps: 1) Verifying the client-side validation and user alert on the Payments Dashboard when a user attempts to approve a refund with missing ACH info. 2) Verifying the server-side enforcement in the `approvePaymentFirstStage` action to prevent such payments from being approved. 3) Adding a final safeguard filter on the Banking Dashboard client to hide any such records that might have erroneously passed the approval stage. This multi-layered approach ensures data integrity and a correct user experience.

## Implementation Plan

**Step 1: Verify Client-Side Validation Alert on Payments Dashboard**  
In the `handleApprove` function, the existing `getBankingInfoError` helper function is called to check if a refund payment has the required banking details. This step is to verify that this check correctly blocks the UI action and displays a `toast.error()` notification to the user if they attempt to approve a refund missing ACH details, as per the acceptance criteria. The relevant code is around lines 1324-1329.
Files: `app/dashboard/payments/payments-client.tsx`

**Step 2: Verify Server-Side Banking Info Validation on Approval**  
In the `approvePaymentFirstStage` server action, verify that the call to `validateRefundBankingInfo` (around line 316) correctly blocks the approval of any party refund payment (e.g., `REFUND_TO_PREVAILING_PARTY`, `PARTY_REFUND_IP`, `PARTY_REFUND_NIP`) that lacks a `bankingSnapshot` or `outgoingBankId`. The action should return a `success: false` result with an informative error message if validation fails, preventing the payment's status from being updated to `APPROVED`. This is the primary backend enforcement of the business rule.
Files: `lib/actions/payment-approvals.ts`

**Step 3: Implement Safeguard Filter on Banking Dashboard**  
To ensure the Banking Dashboard view filters out any records where the banking snapshot failed to attach, add a client-side filter to the `BankingClient` component. This filter will act as a safeguard. Modify the component to filter the `approvedPayments` array to exclude any outgoing party refunds that do not have a valid `bankingSnapshot` object. A banking snapshot can be considered invalid if it's null, undefined, or an empty object. This directly addresses the second acceptance criterion.
Files: `app/dashboard/banking/banking-client.tsx`

**Risk Level:** LOW — The changes are primarily focused on adding and verifying validation logic in both the client and server, with a final UI filter as a safeguard. The core business logic for payments is not being altered, only the conditions under which a refund can be approved. The exploration report shows that the necessary hooks for this validation are already in place, reducing the risk of introducing new bugs.

## Proposed Code Changes

### `app/dashboard/banking/banking-client.tsx` (modify)
As per the implementation plan, this change introduces a client-side safeguard to filter out any outgoing refund payments that have reached the banking dashboard without a valid `bankingSnapshot`. The ticket notes that such payments are erroneously appearing, and this filter will hide them from the view. This directly addresses the acceptance criterion to "Ensure the Banking Dashboard view filters out any records where the banking snapshot failed to attach" by checking that the `bankingSnapshot` is not null, undefined, or an empty object for relevant refund types.
```
--- a/app/dashboard/banking/banking-client.tsx
+++ b/app/dashboard/banking/banking-client.tsx
@@ -453,8 +453,24 @@
     router.refresh();
   };
 
-  // Payments are already filtered server-side, so we use them directly
-  const filteredPayments = approvedPayments;
+  // Payments are filtered server-side, but as a safeguard, we also filter out
+  // any outgoing refunds that are missing a banking snapshot on the client.
+  const filteredPayments = approvedPayments.filter((payment) => {
+    const isPartyRefund = [
+      "REFUND_TO_PREVAILING_PARTY",
+      "PARTY_REFUND_IP",
+      "PARTY_REFUND_NIP",
+    ].includes(payment.type);
+
+    if (isPartyRefund && payment.direction === "OUTGOING") {
+      // A valid banking snapshot must exist and not be an empty object to be processed.
+      return (
+        payment.bankingSnapshot && Object.keys(payment.bankingSnapshot).length > 0
+      );
+    }
+
+    return true;
+  });
 
   // Calculate how many payments on current page will be included in NACHA
   // Exclude payments already linked to a NACHA batch
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest / @testing-library/react`

- **shouldRenderOutgoingRefundsWithValidBankingSnapshots** — This test verifies the happy path, ensuring that legitimate, valid refund records are displayed correctly on the banking dashboard.
- **shouldFilterOutOutgoingRefundsWithMissingBankingSnapshots** *(edge case)* — This is a regression test for the bug described in IDRE-558. It ensures that the new client-side filter correctly hides outgoing refunds that are missing the banking snapshot data.
- **shouldFilterOutOutgoingRefundsWithEmptyBankingSnapshotObject** *(edge case)* — This test covers an edge case identified in the code changes where the snapshot might exist as an empty object instead of null. It ensures the filter is robust enough to handle this case.
- **shouldNotFilterNonRefundPaymentsThatLackBankingSnapshots** *(edge case)* — This test verifies the boundary condition of the filter logic, ensuring it does not incorrectly hide other types of payments that are not expected to have a banking snapshot.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD establishes the core business rule that the ticket (IDRE-558) is trying to enforce. Section 5.2, "Banking Account Binding," explicitly states that no payment can be initiated without a verified banking record on the organization. Section 10.1 proposes the data model changes, including a "banking_verified" flag, that support this rule.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This document outlines the standard end-to-end testing workflow, specifically the "happy path" for refunds in section 5. It confirms the expected sequence of events: a refund is created, then approved in the Payment Dashboard, and only then moves to the Banking tab for NACHA generation. The ticket's goal is to enforce data validation within this established flow.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be reviewed to ensure the implemented solution for validating banking information aligns with the data model and rules specified in section 10.1 (Data Model Changes).
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: The E2E checklist in section 5.1 should be updated to include an "unhappy path" test case for attempting to approve a refund when banking information is missing, verifying that the new alert appears and the status transition is blocked.
- IDRE Worflow: The "Payments" and "Closure" phases of the workflow could be updated to explicitly mention that verified banking information is a prerequisite for processing refunds, making the high-level process description more accurate.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._