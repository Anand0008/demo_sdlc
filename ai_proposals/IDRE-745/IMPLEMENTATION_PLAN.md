## IDRE-745:  Invoice PDF Displaying Incorrect Balance Due Amount for DISP

**Jira Ticket:** [IDRE-745](https://orchidsoftware.atlassian.net//browse/IDRE-745)

## Summary
This plan addresses a bug where the generated invoice PDF displays an incorrect "Amount Paid" and "Balance Due". The issue stems from incorrect data preparation within the `InvoiceDetailsView` component before it calls the PDF generation utility. The fix involves correcting the client-side calculation of `amountPaid`, `balanceDue`, and invoice item amounts in the event handler that generates the PDF, ensuring the data passed to the PDF utility matches the correct data displayed on the UI.

## Implementation Plan

**Step 1: Locate the PDF Generation Handler**  
In the `InvoiceDetailsView` component, locate the event handler function that triggers the invoice PDF download. This function prepares a data object to be passed to the `generateInvoicePDF` utility. The bug originates in how this data object is constructed.
Files: `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx`

**Step 2: Correct the 'amountPaid' Calculation**  
Within the PDF generation handler, find the logic that calculates the `amountPaid`. The bug description and screenshots indicate this value is being set incorrectly (e.g., set to the total amount or another erroneous value). Modify the logic to correctly calculate the sum of successful payments associated with the invoice. The correct payment data should be available from the `invoice` prop, as the rest of the UI displays the correct balance.
Files: `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx`

**Step 3: Update the 'balanceDue' Calculation**  
After ensuring `amountPaid` is calculated correctly, update the calculation for `balanceDue`. It should be the `invoice.totalAmount` minus the newly corrected `amountPaid`.
Files: `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx`

**Step 4: Verify Invoice Item Amounts for PDF Data**  
The attached screenshots show that the line item amounts on the PDF are also incorrect. Review the mapping of `invoice.invoiceItems` from the component's props to the data object for the PDF. Ensure that the `amount` for each line item is being correctly passed from the source `invoiceItems` array.
Files: `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx`

**Risk Level:** LOW — The proposed change is confined to a client-side component and only affects the data mapping for a non-critical function (PDF export). It does not alter any backend logic, database schemas, or the primary UI display of financial information, which is already confirmed to be correct. The risk of regression or unintended side effects is minimal.

## Proposed Code Changes

### `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx` (modify)
The data object being prepared for the `generateInvoicePDF` function was incorrectly using `invoice.totalAmount` for the `amountPaid`, `balanceDue`, and individual line item amounts. This caused the generated PDF to show incorrect financial details. The fix replaces these hardcoded incorrect values with the correct variables (`amountPaid`, `balanceDue`, and `item.amount`) which are already calculated and used to display the correct information in the component's UI.
```
--- a/app/app/invoices/[invoiceId]/components/invoice-details-view.tsx
+++ b/app/app/invoices/[invoiceId]/components/invoice-details-view.tsx
@@ -413,14 +413,14 @@
       items: invoice.invoiceItems.map((item) => ({
         description: item.description || `Case Fee: ${item.case.caseNumber}`,
         quantity: 1,
-        unitPrice: invoice.totalAmount,
-        amount: invoice.totalAmount,
+        unitPrice: item.amount,
+        amount: item.amount,
       })),
       subtotal: invoice.totalAmount,
       total: invoice.totalAmount,
-      amountPaid: invoice.totalAmount,
-      balanceDue: invoice.totalAmount,
+      amountPaid: amountPaid,
+      balanceDue: balanceDue,
       notes: invoice.notes,
       status: invoice.status,
     };
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldCallGenerateInvoicePDFWithCorrectBalanceForPartiallyPaidInvoice** — This is the primary regression test. It simulates the exact scenario reported in the bug: a partially paid invoice where the balance due was being calculated incorrectly for the PDF. This test ensures the corrected values are passed to the PDF generation utility.
- **shouldCallGenerateInvoicePDFWithZeroBalanceForFullyPaidInvoice** — This test case verifies that the component behaves correctly for a fully paid invoice, ensuring the fix for partial payments did not introduce a regression for this common scenario.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page explicitly identifies the 'Payments & Refunds Logic' as a 'major complexity hotspot' prone to miscalculations. This provides critical context that the bug in ticket IDRE-745 is part of a known pattern of complex and error-prone functionality, advising the developer to be cautious and thorough.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This document outlines the end-to-end business process, including the 'payment collection' phase. Understanding this workflow is necessary to identify where in the process the invoice PDF is generated and what data should be available at that stage for calculating the balance due.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This page provides an operational constraint relevant to the ticket. It explicitly lists 'PDF Handling' as a required step in the E2E testing workflow, which the developer must ensure is completed before the bug fix can be deployed to production.

**Suggested Documentation Updates:**

- IDRE Worflow: The root cause of the bug may stem from a misunderstanding of the payment and invoicing lifecycle. This document should be updated to clarify the precise business rules for how partial payments, credits, and fees are aggregated to calculate the final 'Balance Due' on an invoice at the time of generation.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._