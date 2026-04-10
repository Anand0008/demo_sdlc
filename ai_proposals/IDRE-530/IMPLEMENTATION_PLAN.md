## IDRE-530: Ineligible Disputes: Invoices are automatically storing and blocking system payments

**Jira Ticket:** [IDRE-530](https://orchidsoftware.atlassian.net//browse/IDRE-530)

## Summary
Fix the issue where ineligible dispute invoices are stored and block system payments. The solution stops storing these invoices in the database (sending them via email only) and filters out any legacy stored ineligible invoices from the UI and payment blocking logic.

## Implementation Plan

**Step 1: Stop Storing Ineligible Invoices**  
Modify `sendAllIneligibilityEmails` (and any underlying invoice generation logic it calls) to prevent storing the invoice in the database. Generate the invoice PDF in-memory and attach it directly to the email, removing the `prisma.invoice.create` call for ineligible cases.
Files: `lib/actions/send-ineligibility-emails-action.ts`

**Step 2: Hide Legacy Ineligible Invoices from UI**  
Update the `getPendingInvoices` action (or the filtering logic in `pending-invoices-section.tsx`) to exclude any existing legacy invoices where the associated case status is `INELIGIBLE`. This ensures they no longer appear on the user side.
Files: `lib/actions/index.ts`, `app/app/payments/components/pending-invoices-section.tsx`

**Step 3: Prevent Legacy Invoices from Blocking Payments**  
Update the payment page logic that checks for blocking invoices. Ensure that any legacy invoices associated with ineligible cases are filtered out and ignored, allowing users to fully interact with their cases for payment without being blocked.
Files: `app/app/payments/page.tsx`

**Risk Level:** MEDIUM — Changes involve the payments and invoice engine, which is a known complexity hotspot. Modifying how invoices are stored and filtered requires careful testing to ensure valid invoices are not accidentally hidden or skipped.

**Deployment Notes:**
- Ensure that the email service can handle generating and attaching the invoice PDF in-memory without relying on a stored database record.

## Proposed Code Changes

### `lib/actions/send-ineligibility-emails-action.ts` (modify)
Ineligible invoices should only be emailed and never stored in the database, as storing them automatically blocks system payments. We generate the PDF in-memory using the invoice data instead of a persisted database record.
```typescript
--- a/lib/actions/send-ineligibility-emails-action.ts
+++ b/lib/actions/send-ineligibility-emails-action.ts
@@ -...@@
-    const invoice = await prisma.invoice.create({
-      data: {
-        caseId: caseRecord.id,
-        partyId: party.id,
-        amount: amount,
-        status: 'UNPAID',
-        // ... other invoice fields
-      }
-    });
-    
-    const pdfBuffer = await generateInvoicePdf(invoice);
+    // Generate invoice PDF in-memory without storing in the database
+    // to prevent blocking system payments for ineligible cases
+    const invoiceData = {
+      caseId: caseRecord.id,
+      partyId: party.id,
+      amount: amount,
+      status: 'UNPAID',
+      // ... other invoice fields
+    };
+    
+    const pdfBuffer = await generateInvoicePdf(invoiceData);
```

### `lib/actions/index.ts` (modify)
Filters out any legacy stored ineligible invoices from the pending invoices query so they no longer appear on the user side.
```typescript
--- a/lib/actions/index.ts
+++ b/lib/actions/index.ts
@@ -...@@
 export async function getPendingInvoices(userId: string) {
   return prisma.invoice.findMany({
     where: {
       partyId: userId,
       status: 'UNPAID',
+      case: {
+        status: {
+          not: 'INELIGIBLE'
+        }
+      }
     },
     include: {
       case: true
     }
   });
 }
```

### `app/app/payments/components/pending-invoices-section.tsx` (modify)
Adds a client-side/component-level safeguard to ensure legacy ineligible invoices are hidden from the UI.
```
--- a/app/app/payments/components/pending-invoices-section.tsx
+++ b/app/app/payments/components/pending-invoices-section.tsx
@@ -...@@
-  const pendingInvoices = invoices.filter(invoice => invoice.status === 'UNPAID');
+  const pendingInvoices = invoices.filter(invoice => 
+    invoice.status === 'UNPAID' && invoice.case?.status !== 'INELIGIBLE'
+  );
```

### `app/app/payments/page.tsx` (modify)
Updates the payment page logic that checks for blocking invoices to explicitly ignore any legacy invoices associated with ineligible cases, allowing users to fully interact with their cases for payment.
```
--- a/app/app/payments/page.tsx
+++ b/app/app/payments/page.tsx
@@ -...@@
   const blockingInvoices = await prisma.invoice.findMany({
     where: {
       partyId: user.id,
-      status: 'UNPAID'
+      status: 'UNPAID',
+      case: {
+        status: {
+          not: 'INELIGIBLE'
+        }
+      }
     }
   });
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest with React Testing Library`

- **should email the ineligible invoice without storing it in the database** — Verifies that ineligible invoices are emailed to users but never persisted to the database, preventing them from blocking future payments.
- **should filter out legacy ineligible invoices from pending invoices query** *(edge case)* — Ensures that any legacy ineligible invoices already in the database are filtered out at the query level.
- **should not render legacy ineligible invoices in the pending invoices section** *(edge case)* — Client-side safeguard to ensure legacy ineligible invoices are never displayed to the user.
- **should not block system payments when only legacy ineligible invoices exist** *(edge case)* — Verifies that the presence of legacy ineligible invoices does not trigger the payment blocking logic on the payments page.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — Identifies the payments and refunds engine as a major complexity hotspot, specifically highlighting the need to test 'Ineligible' closure types combined with 'invoice' payments. This is directly relevant to the ticket's goal of changing how ineligible invoices affect payment blocking.

**Suggested Documentation Updates:**

- Bugs - The QA test matrices and focus ideas will need to be updated to reflect that invoices for Ineligible disputes no longer block payments and are not stored on the party side.
- IDRE Worflow - May need updating if the current end-to-end case lifecycle documentation specifies that ineligible invoices block payments or appear on the user side.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._