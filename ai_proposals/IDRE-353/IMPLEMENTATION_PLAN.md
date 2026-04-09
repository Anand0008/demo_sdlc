## IDRE-353: Change CMS Payment Validation Logic

**Jira Ticket:** [IDRE-353](https://orchidsoftware.atlassian.net//browse/IDRE-353)

## Summary
Implement CMS payment reconciliation by adding Excel file parsing, 1-to-1 matching with exception handling, and a passive status update to 'Paid (Reconciled)' with external reference logging.

## Implementation Plan

**Step 1: Add Excel Upload and Reference Input**  
Add a file upload input for the monthly CMS Excel file and a text input for the 'External Reference' (e.g., Check #, Wire Transfer ID). Implement parsing logic to extract Dispute IDs and Amounts from the uploaded file.
Files: `components/cms/process-cms-invoice-dialog.tsx`

**Step 2: Implement Matching and Exception Handling**  
Implement 1-to-1 matching logic comparing the parsed Excel data against the `pendingPayments` state. Create an 'Exceptions' view in the dialog to flag and display any Dispute IDs from the file that are missing in the portal or have mismatched amounts.
Files: `components/cms/process-cms-invoice-dialog.tsx`

**Step 3: Create Backend Reconciliation Action**  
Add a new server action `reconcileCmsPayments(paymentIds: string[], externalReference: string)` that updates the status of the specified payments to `PAID` and stores the `externalReference` in the payment's metadata or notes field. Ensure this function strictly performs database updates and does NOT trigger any external payment processing APIs.
Files: `lib/actions/payment.ts`

**Step 4: Integrate Reconciliation Action in Dialog**  
Update the dialog's submit handler to call the new `reconcileCmsPayments` action with the successfully matched payment IDs and the provided external reference, then close the dialog and refresh the pending payments list.
Files: `components/cms/process-cms-invoice-dialog.tsx`

**Risk Level:** LOW — The changes are isolated to the CMS reconciliation dialog and a new specific backend action. By explicitly avoiding external API calls, the risk of accidental funds transfer is mitigated.

**Deployment Notes:**
- Ensure any new dependencies for Excel parsing (if added) are included in package.json.

## Proposed Code Changes

### `components/cms/process-cms-invoice-dialog.tsx` (modify)
No rationale provided
```
Type: modify

```diff
--- a/components/cms/process-cms-invoice-dialog.tsx
+++ b/components/cms/process-cms-invoice-dialog.tsx
@@ -34,6 +34,8 @@
 import { getPendingCmsPayments, processCmsInvoice } from "@/lib/actions/cms-invoice";
 import { type CmsInvoice, type PendingCmsPayment, type CmsInvoiceStatus } from "@/lib/cms-utils";
 import { toast } from "sonner";
+import { reconcileCmsPayments } from "@/lib/actions/payment";
+import * as XLSX from "xlsx";
 
 interface ProcessCmsInvoiceDialogProps {
   invoice: CmsInvoice | null;
@@ -49,6 +51,10 @@
   const [loading, setLoading] = useState(false);
   const [fetchingPayments, setFetchingPayments] = useState(false);
   const [autoSelectedAmount, setAutoSelectedAmount] = useState(0);
+  const [externalReference, setExternalReference] = useState("");
+  const [excelData, setExcelData
```

## Test Suggestions

Framework: `Vitest with React Testing Library`

- **should successfully process a valid CMS invoice and update status to Paid (Reconciled)** — Verifies the happy path where a CMS invoice perfectly matches internal pending transactions and successfully updates the status.
- **should flag transactions as Exceptions when billed amount differs from internal record** *(edge case)* — Verifies that the system correctly identifies and flags amount mismatches between the CMS invoice and internal records.
- **should flag transactions as Exceptions when Dispute ID is missing from portal** *(edge case)* — Verifies that the system correctly handles CMS invoice line items that do not correspond to any recognized pending transactions in the portal.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — Highlights that the payments engine and status transitions are a major complexity hotspot, which is crucial context when introducing the new "Paid (Reconciled)" status and amount validation logic.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Defines the canonical end-to-end case lifecycle, including the payment collection phase, which will be impacted by the new CMS reconciliation process and status updates.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — Outlines the high-level case workflow, specifically mentioning the Payment Collection phase where the new CMS payment validation logic will reside.

**Suggested Documentation Updates:**

- "IDRE Worflow": Needs to be updated to include the new "Paid (Reconciled)" status and the CMS Excel file reconciliation step.
- "IDRE Case Workflow Documentation": Should be updated to reflect the new reconciliation process and exception handling within the Payment Collection phase.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._