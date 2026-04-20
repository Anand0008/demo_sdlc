## IDRE-530: Ineligible Disputes: Invoices are automatically storing and blocking system payments

**Jira Ticket:** [IDRE-530](https://orchidsoftware.atlassian.net//browse/IDRE-530)

## Summary
This plan resolves the issue of invoices for ineligible disputes blocking system payments by altering their creation process. Instead of creating a persistent invoice record in the database, the implementation will construct an in-memory invoice object. This transient object will be used solely to generate the required PDF for the email notification. This prevents the invoice from being stored, thus ensuring it does not appear on the user's dashboard or block other payments, directly fulfilling the ticket's requirements without altering UI components or other data-fetching logic. An existing cleanup task that cancels old, incorrectly-stored invoices will be preserved.

## Implementation Plan

**Step 1: Remove Database Persistence for Ineligibility Invoices**  
In the `sendIneligibilityEmailsInternal` function, remove the database queries that find or create an `Invoice` record for ineligible cases. This includes the `prisma.invoice.findFirst` call around line 235 and the `prisma.invoice.create` call around line 294. The logic to cancel legacy `STANDARD` type invoices (lines 212-231) should be kept for data cleanup.
Files: `lib/actions/send-ineligibility-emails-action.ts`

**Step 2: Construct In-Memory Invoice Object for PDF Generation**  
In place of the removed database calls, construct a transient JavaScript object that mimics the structure of the `invoiceRecord` previously returned by Prisma. Use the existing logic for generating `invoiceNumber`, `adminFeeDollars`, and `dueDate`. Populate the object and its nested `invoiceItems` and `case` properties using data already available in the `caseData` function parameter. The structure should match the `include` clause of the original Prisma query.
Files: `lib/actions/send-ineligibility-emails-action.ts`

**Step 3: Generate PDF from In-Memory Invoice Data**  
Pass the newly created in-memory invoice object to the `generateInvoicePDFBuffer` function around line 349. The rest of the logic for creating the PDF attachment and sending the email will remain the same, ensuring the user still receives the invoice via email as required.
Files: `lib/actions/send-ineligibility-emails-action.ts`

**Risk Level:** LOW — The change is highly localized to a single server action for a specific business process (handling ineligible cases). It removes a database write, which is a low-risk operation compared to modifying data. The core user-facing functionality (receiving an invoice via email) is preserved. The risk of unintended side effects is minimal as we are preventing the creation of data that was causing issues elsewhere.

## Proposed Code Changes

### `lib/actions/send-ineligibility-emails-action.ts` (modify)
This change prevents invoices for ineligible disputes from being stored in the database. By removing the `prisma.invoice.findFirst` and `prisma.invoice.create` calls and instead constructing a transient, in-memory invoice object, we fulfill the ticket's requirement. This object is used solely for generating the PDF to be emailed, ensuring users receive the necessary document without creating a persistent record that blocks system payments or appears on the party's dashboard. The existing logic to cancel legacy `STANDARD` type invoices is preserved for data cleanup.
```typescript
--- a/lib/actions/send-ineligibility-emails-action.ts
+++ b/lib/actions/send-ineligibility-emails-action.ts
@@ -230,115 +230,52 @@
           );
         }
 
-        // Check if an invoice already exists for this case and party type
-        // Look for invoices with MISSING_BANK_INFO type that have an invoice item for this case
-        let invoiceRecord = await prisma.invoice.findFirst({
-          where: {
-            organizationId: organizationId || undefined,
-            type: InvoiceType.MISSING_BANK_INFO,
-            invoiceItems: {
-              some: {
-                caseId: caseData.id,
-                description: {
-                  contains: "Ineligibility admin fee",
-                },
-              },
-            },
-          },
-          include: {
-            invoiceItems: {
-              include: {
-                case: {
-                  select: {
-                    id: true,
-                    disputeReferenceNumber: true,
-                    status: true,
-                    createdAt: true,
-                    initiatingParty: {
-                      select: {
-                        name: true,
-                        email: true,
-                      },
-                    },
-                    nonInitiatingParty: {
-                      select: {
-                        name: true,
-                        email: true,
-                      },
-                    },
-                    DisputeLineItems: true,
-                  },
-                },
-              },
-            },
-          },
-        });
+        // Generate a transient invoice number for the PDF. This is not stored.
+        const year = new Date().getFullYear();
+        const sequenceNum = Date.now().toString().slice(-4);
+        const invoiceNumber = `INELIG-${caseData.id.substring(0, 8).toUpperCase()}-${year}-${sequenceNum}`;
+        const dueDate = normalizeToEndOfDay(addBusinessDays(new Date(), 10));
 
-        // If no 
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldEmailAnInMemoryInvoiceWithoutStoringItInTheDatabase** — This test verifies the core requirement of the ticket: an invoice is generated for the email notification but is never saved to the database, thus preventing it from blocking future payments.
- **shouldCancelExistingStandardInvoicesWhenProcessingIneligibleDispute** *(edge case)* — The implementation plan notes that an existing cleanup task for old, incorrectly-stored invoices should be preserved. This test ensures that this legacy logic is not broken by the new changes.
- **shouldNotStoreInvoiceIfEmailServiceFails** *(edge case)* — This test ensures that if a downstream dependency like the email service fails, the system handles the error gracefully and does not perform partial operations that would corrupt data (i.e., create an orphaned invoice).

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the canonical end-to-end case lifecycle. It states that when a case is marked 'Ineligible', it is closed immediately with 'No fee reallocation', which contradicts the ticket's premise that an invoice is being generated. This is a core business rule the developer must be aware of.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page contains a detailed QA checklist for the case lifecycle. Section 2.4, 'No payments / fees after ineligible', explicitly states that for ineligible cases, 'No administrative fee invoices are generated' and 'No payment due is displayed'. This provides a clear, testable requirement that directly contradicts the behavior described in the ticket.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This document presents a conflicting business rule. It defines a specific status, 'INELIGIBLE_PENDING_ADMIN_FEE', where a $115 admin fee must be collected from the Initiating Party for an ineligible case. This contradicts other documentation but aligns with the ticket's statement that an invoice is generated, providing critical context about the system's intended (but possibly incorrect) logic.

**Suggested Documentation Updates:**

- IDRE Worflow
- Bugs
- IDRE Case Workflow Documentation

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._