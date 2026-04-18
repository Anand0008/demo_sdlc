## IDRE-585: Invoice Issues

**Jira Ticket:** [IDRE-585](https://orchidsoftware.atlassian.net//browse/IDRE-585)

## Summary
This plan addresses the inconsistency between disputes shown on the payments page and those available for invoicing. The root cause is likely two separate server actions in `lib/actions/party-payments.ts` using different filtering logic. The plan is to unify the Prisma queries in `getUnbilledCases` and the action fetching payable cases to ensure they return the same set of disputes. A new integration test will be added to `tests/actions/case-balance-actions.test.ts` to verify the correct behavior when invoices are created and cancelled, preventing future regressions.

## Implementation Plan

**Step 1: Locate and Analyze Discrepant Data Fetching Logic**  
In `lib/actions/party-payments.ts`, locate the function `getUnbilledCases` and the corresponding function that fetches cases for the main payments page (e.g., `getCasesForPayment`). Carefully compare the Prisma query `where` clauses in both functions. The discrepancy is expected to be in how they filter cases based on their association with existing invoices via the `invoiceItems` relation and the status of the linked invoice.
Files: `lib/actions/party-payments.ts`

**Step 2: Unify Case Filtering Logic**  
Refactor the Prisma queries in both `getUnbilledCases` and the function for fetching payable cases to use a shared, consistent filtering logic. The unified logic must ensure that a case is considered payable/invoiceable only if it has a balance due and is not associated with any invoice that has a status other than `CANCELLED`. This will synchronize the data presented on the payments page and in the create invoice dialog.
Files: `lib/actions/party-payments.ts`

**Step 3: Add Integration Test for Invoice Lifecycle**  
Add a new test suite to `tests/actions/case-balance-actions.test.ts` to validate the fix. The test should simulate the full lifecycle described in the ticket: 1. Create a case requiring payment. 2. Verify it appears in both "payable" and "unbilled" lists. 3. Create an invoice for the case. 4. Verify the case is removed from both lists. 5. Cancel the invoice. 6. Verify the case reappears in both lists. This will prevent future regressions.
Files: `tests/actions/case-balance-actions.test.ts`

**Risk Level:** MEDIUM — The change touches core payment and invoicing logic, which is a sensitive area of the application. An error in the filtering logic could result in users being unable to pay for disputes or incorrect invoices being generated. The medium risk is mitigated by adding a comprehensive integration test.

## Proposed Code Changes

### `lib/actions/party-payments.ts` (modify)
This change introduces a shared `unbilledCaseClause` to correctly filter cases based on their invoice status. Previously, `getPartyCasesForPayment` did not check for invoices, and `getUnbilledCases` used an incorrect filter that excluded cases on cancelled invoices. Applying this unified logic to both functions ensures data consistency across the payments page and the invoice creation form, directly addressing the bug reported in the ticket.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -1,5 +1,6 @@
 "use server";
 
+import { InvoiceStatus, Prisma } from "@prisma/client";
 import { z } from "zod";
 import { prisma } from "@/lib/prisma";
 import { getSession, getOrganizationId } from "@/lib/auth";
@@ -10,6 +11,19 @@
   ActionError,
   handleActionError,
 } from "@/lib/errors/action-errors";
+
+/**
+ * Common Prisma clause to find cases that are not on an active invoice.
+ * A case is considered "unbilled" or "payable" if it has no invoice items,
+ * or if all invoice items it belongs to are on invoices with a CANCELLED status.
+ */
+const unbilledCaseClause = {
+  invoiceItems: {
+    none: {
+      invoice: {
+        status: { not: InvoiceStatus.CANCELLED },
+      },
+    },
+  },
+};
 
 const GetPartyCasesForPaymentSchema = z.object({
   page: z.number().min(1).default(1),
@@ -51,6 +65,7 @@
     amountDue: {
       gt: 0,
     },
+    ...unbilledCaseClause,
   };
 
   if (filters.organizationId && filters.organizationId !== "all") {
@@ -140,9 +155,7 @@
     amountDue: {
       gt: 0,
     },
-    invoiceItems: {
-      none: {},
-    },
+    ...unbilledCaseClause,
   };
 
   if (organizationId) {
```

### `tests/actions/case-balance-actions.test.ts` (modify)
This new test suite validates the fix by simulating the entire lifecycle described in the ticket. It confirms that a case with a balance is initially available for payment, disappears after an invoice is created, and reappears once that invoice is cancelled. This ensures the unified logic works as expected and protects against future regressions.
```typescript
--- a/tests/actions/case-balance-actions.test.ts
+++ b/tests/actions/case-balance-actions.test.ts
@@ -1,11 +1,22 @@
-import { describe, test, expect, beforeAll, afterAll } from "vitest";
-import { createTestUser, createTestOrganization } from "../test-utils";
-import { User, Organization, Case, CaseFee, FeeType } from "@prisma/client";
+import { describe, test, expect, beforeAll, afterAll, beforeEach } from "vitest";
+import {
+  createTestUser,
+  createTestOrganization,
+  cleanupDatabase,
+  createTestCase,
+} from "../test-utils";
+import { User, Organization, Case, FeeType } from "@prisma/client";
 import { prisma } from "@/lib/prisma";
 import {
   getCaseBalanceSummary,
   getCaseLedger,
 } from "@/lib/actions/party-case-details";
+import {
+  getPartyCasesForPayment,
+  getUnbilledCases,
+} from "@/lib/actions/party-payments";
+import { createInvoiceFromCases } from "@/lib/actions/invoicing";
 
 let user: User;
 let organization: Organization;
@@ -15,7 +26,7 @@
 });
 
 afterAll(async () => {
-  // Clean up test data
+  await cleanupDatabase();
 });
 
 describe("getCaseBalanceSummary", () => {
@@ -74,3 +85,98 @@
     expect(ledger.length).toBe(2);
   });
 });
+
+describe("Invoice Lifecycle and Case Visibility", () => {
+  let testCase: Case;
+
+  beforeEach(async () => {
+    // Setup: create a case with a balance
+    const newCase = await createTestCase(organization.id, user.id);
+    await prisma.caseFee.create({
+      data: {
+        caseId: newCase.id,
+        feeType: FeeType.FILING_FEE,
+        amount: 10000, // $100.00
+        isPaid: false,
+      },
+    });
+    // Update case amountDue
+    testCase = await prisma.case.update({
+      where: { id: newCase.id },
+      data: { amountDue: 10000 },
+    });
+  });
+
+  test("cases should appear and disappear from payable/unbilled lists as invoices are created and cancelled", async () => {
+    // Step 1: Verify case is initially available for payment and invoicing
+    let payableCases = await g
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Jest`

- **shouldMakeCaseAvailableForPaymentAgainAfterItsInvoiceIsCancelled** *(edge case)* — This is the primary regression test. It simulates the exact lifecycle described in the ticket: a case is invoiced (removing it from the payment list) and then the invoice is cancelled, which should make the case available for payment again. This validates the fix in `unbilledCaseClause` that now correctly includes cases associated with cancelled invoices.
- **shouldReturnIdenticalCasesForPaymentAndInvoicing** — This test verifies that the two key functions, one for fetching cases to display on the payments tab (`getPartyCasesForPayment`) and one for fetching cases to add to a new invoice (`getUnbilledCases`), now return the exact same set of cases. This directly addresses the data inconsistency bug.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the canonical end-to-end case lifecycle, including payment collection. The ticket addresses a bug in this workflow, where the status of disputes is not handled consistently during invoicing. A developer needs to understand the expected process flow described here to correctly implement the fix.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page provides critical context, identifying the 'Payments & Refunds Logic / Workflow' as a 'major complexity hotspot' prone to high-impact production issues. This directly relates to the invoice inconsistency bug in the ticket and warns the developer about the risks and the need for thorough regression testing around case status transitions.

**Suggested Documentation Updates:**

- IDRE Worflow: This document outlines the end-to-end case lifecycle. It should be updated to explicitly describe the state transitions for disputes when an invoice is created or deleted, ensuring the documentation matches the implemented logic.

## AI Confidence Scores
Plan: 70%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._