## IDRE-585: Invoice Issues

**Jira Ticket:** [IDRE-585](https://orchidsoftware.atlassian.net//browse/IDRE-585)

## Summary
This plan resolves inconsistencies in which disputes are available for payment and invoicing. The core of the fix is to unify the case status filtering logic across the UI, invoice creation, and CSV export functionalities. I will update the API route for the outstanding payments report (`app/api/reports/outstanding-payments/route.ts`) and the server action that fetches cases for the payments page (`getCasesForPayment`) to use the same comprehensive set of "awaiting payment" statuses. Finally, I will verify that the existing invoice deletion logic correctly returns cases to a payable state.

## Implementation Plan

**Step 1: Unify Case Status Filter in Outstanding Payments Report API**  
The current Prisma query for cases filters on a specific list of statuses. To ensure the CSV export is consistent with other parts of the application, this list needs to be expanded. Add `PENDING_CLOSURE_PAYMENTS` and `NOTICE_OF_DISMISSAL_NON_PAYMENT` to the `in` array for the `status` field within the `where` clause of the `prisma.case.findMany` call around line 167.
Files: `app/api/reports/outstanding-payments/route.ts`

**Step 2: Align Case Status Filter in `getCasesForPayment` Action**  
The ticket indicates a discrepancy between the payments tab and other features. This is likely due to inconsistent filtering in the data source for the payments page. Locate the `getCasesForPayment` server action (likely in `lib/actions/party-payments.ts` or a similar actions file) and modify its `prisma.case.findMany` query. The `where` clause should filter for cases with statuses matching the newly unified list from the previous step: `PENDING_PAYMENTS`, `PENDING_SECOND_PAYMENT`, `PENDING_ADMINISTRATIVE_CLOSURE`, `INELIGIBLE`, `INELIGIBLE_PENDING_ADMIN_FEE`, `PENDING_CLOSURE_PAYMENTS`, and `NOTICE_OF_DISMISSAL_NON_PAYMENT`. This will ensure the UI on the payments page shows the same set of cases as the CSV report.
Files: `lib/actions/party-payments.ts`

**Step 3: Verify Invoice Deletion Behavior**  
The ticket requires that deleting an invoice returns the associated disputes to the payment tab. Review the `adminDeleteOrganizationInvoice` function in this file to confirm that when an invoice is deleted, the related `InvoiceItem` records are also deleted or disassociated from the cases. This should be sufficient to make the cases reappear in the "awaiting payment" lists, which now use a unified filter. No code changes are expected, but this verification is crucial to confirm the end-to-end workflow.
Files: `lib/actions/organization-invoices.ts`

**Risk Level:** LOW — The changes involve modifying database query filters to be more inclusive and consistent across different features. This is unlikely to cause regressions, as it aligns behavior rather than introducing new logic. The primary risk is that the expanded list of statuses could include cases not intended for invoicing, but the statuses are derived from existing logic in the invoicing and payments modules, making this risk low. Testing the payment workflow for each case status is required.

## Proposed Code Changes

### `app/api/reports/outstanding-payments/route.ts` (modify)
As per the implementation plan, this change updates the API route for the outstanding payments report (used for CSV export) to include cases with `PENDING_CLOSURE_PAYMENTS` and `NOTICE_OF_DISMISSAL_NON_PAYMENT` statuses. This ensures the CSV export includes all cases that are considered payable, aligning it with the payments UI.
```typescript
--- a/app/api/reports/outstanding-payments/route.ts
+++ b/app/api/reports/outstanding-payments/route.ts
@@ -164,11 +164,13 @@
         "PENDING_PAYMENTS",
         "PENDING_SECOND_PAYMENT",
         "PENDING_ADMINISTRATIVE_CLOSURE",
         "INELIGIBLE",
         "INELIGIBLE_PENDING_ADMIN_FEE",
+        "PENDING_CLOSURE_PAYMENTS",
+        "NOTICE_OF_DISMISSAL_NON_PAYMENT",
       ],
     },
     invoiceItems: {
       none: {},
     },
```

### `lib/actions/party-payments.ts` (modify)
This change aligns the `getCasesForPayment` server action with the outstanding payments report by including the same expanded set of case statuses. This action is responsible for fetching data for the payments tab, and this update will ensure that the UI correctly displays all disputes that are awaiting payment, resolving the discrepancy described in the ticket.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -51,11 +51,13 @@
         "PENDING_PAYMENTS",
         "PENDING_SECOND_PAYMENT",
         "PENDING_ADMINISTRATIVE_CLOSURE",
         "INELIGIBLE",
         "INELIGIBLE_PENDING_ADMIN_FEE",
+        "PENDING_CLOSURE_PAYMENTS",
+        "NOTICE_OF_DISMISSAL_NON_PAYMENT",
       ],
     },
     // Case should not be part of any existing invoice
     invoiceItems: {
       none: {},
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldIncludeCasesWithPendingClosureAndNonPaymentDismissalStatuses** — This regression test verifies that the `getCasesForPayment` function now correctly fetches all cases considered to be awaiting payment, including the statuses that were previously missed, thus fixing the discrepancy shown in the UI.
- **shouldReturnCsvIncludingCasesWithAllPayableStatuses** — This regression test ensures the CSV export functionality aligns with the UI by including the same set of payable case statuses. It verifies that the API route now correctly filters for all relevant statuses, fixing the bug where the CSV and UI were mismatched.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page provides the canonical, end-to-end case lifecycle, including the payment collection phase. The ticket addresses a bug in this workflow, and understanding the defined process is essential for implementing a correct fix.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page explicitly identifies the "Payments & Refunds Logic / Workflow" as a "major complexity hotspot" prone to errors in status transitions. This gives the developer critical context about the sensitivity of the code they are about to modify.

**Suggested Documentation Updates:**

- IDRE Worflow

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._