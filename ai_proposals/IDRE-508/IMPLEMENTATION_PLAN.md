## IDRE-508: All Emails re: Payments should include Invoice

**Jira Ticket:** [IDRE-508](https://orchidsoftware.atlassian.net//browse/IDRE-508)

## Summary
Update the email generation logic to ensure that invoices are always attached to payment request emails (Initial fees due, Early closure path, Underpayment), regardless of whether the organization has bank account information on file.

## Implementation Plan

**Step 1: Remove bank account condition from email workflow attachments**  
Locate the email preparation functions such as `sendPaymentEmailForCase`, `sendAdministrativeClosureEmails`, and any variance/underpayment email handlers. Find the conditional logic that checks if the organization has bank account information on file before attaching the invoice. Remove this condition to ensure the invoice PDF is always generated and appended to the email attachments array.
Files: `lib/actions/email-workflow.ts`

**Step 2: Ensure unconditional invoice attachment in payment actions and email jobs**  
Review the invocation of `createIDRPaymentEmailJob` and the construction of the `EmailAttachment` array. If there is any logic that omits the invoice attachment based on the presence of a bank account, remove it. Ensure that `generateInvoicePDFBuffer` is called and its output is always included in the attachments payload for payment request emails.
Files: `lib/actions/payment.ts`, `lib/services/email/email-job-service.ts`

**Risk Level:** LOW — The change only affects the payload of outgoing emails by ensuring an attachment is always included. It does not alter core payment processing, database schemas, or state transitions.

## Proposed Code Changes

### `lib/actions/email-workflow.ts` (modify)
Ensure that the invoice PDF is always generated and appended to the email attachments array for payment request emails, regardless of whether the organization has bank account information on file. This applies to initial fees due, early closure path, and underpayment emails.
```typescript
--- a/lib/actions/email-workflow.ts
+++ b/lib/actions/email-workflow.ts
@@ -100,11 +100,9 @@
-    // Check if organization has bank account
-    if (!hasBankAccount) {
-      const invoiceBuffer = await generateInvoicePDFBuffer(invoiceData);
-      attachments.push({
-        filename: `Invoice-${invoiceNumber}.pdf`,
-        content: invoiceBuffer.toString("base64"),
-        contentType: "application/pdf",
-      });
-    }
+    // Always generate and attach invoice
+    const invoiceBuffer = await generateInvoicePDFBuffer(invoiceData);
+    attachments.push({
+      filename: `Invoice-${invoiceNumber}.pdf`,
+      content: invoiceBuffer.toString("base64"),
+      contentType: "application/pdf",
+    });
```

### `lib/actions/payment.ts` (modify)
Remove any logic that omits the invoice attachment based on the presence of a bank account when preparing payment actions. Ensure `generateInvoicePDFBuffer` is called and its output is always included in the attachments payload.
```typescript
--- a/lib/actions/payment.ts
+++ b/lib/actions/payment.ts
@@ -200,11 +200,9 @@
-    // Only attach invoice if no banking info is present
-    if (!hasBankingInfo) {
-      const invoiceBuffer = await generateInvoicePDFBuffer(invoiceData);
-      attachments.push({
-        filename: `Invoice-${invoiceNumber}.pdf`,
-        content: invoiceBuffer.toString("base64"),
-        contentType: "application/pdf",
-      });
-    }
+    // Always generate and attach invoice
+    const invoiceBuffer = await generateInvoicePDFBuffer(invoiceData);
+    attachments.push({
+      filename: `Invoice-${invoiceNumber}.pdf`,
+      content: invoiceBuffer.toString("base64"),
+      contentType: "application/pdf",
+    });
```

### `lib/services/email/email-job-service.ts` (modify)
Ensure that the email job service unconditionally includes the invoice attachment for payment request emails, removing any checks for bank account presence.
```typescript
--- a/lib/services/email/email-job-service.ts
+++ b/lib/services/email/email-job-service.ts
@@ -50,11 +50,9 @@
-    // Conditionally attach invoice
-    if (!hasBankAccount) {
-      const invoiceBuffer = await generateInvoicePDFBuffer(invoiceData);
-      attachments.push({
-        filename: `Invoice-${invoiceNumber}.pdf`,
-        content: invoiceBuffer.toString("base64"),
-        contentType: "application/pdf",
-      });
-    }
+    // Always attach invoice
+    const invoiceBuffer = await generateInvoicePDFBuffer(invoiceData);
+    attachments.push({
+      filename: `Invoice-${invoiceNumber}.pdf`,
+      content: invoiceBuffer.toString("base64"),
+      contentType: "application/pdf",
+    });
```

## Test Suggestions

Framework: `Jest/Vitest`

- **shouldAttachInvoiceToInitialFeesDueEmailWhenOrgHasBankAccount** — Regression test to ensure that the initial fees due email includes the invoice attachment even when the organization has a bank account on file.
- **shouldIncludeInvoiceInUnderpaymentActionAttachmentsRegardlessOfBankAccount** — Regression test to verify that payment actions for underpayments always include the invoice attachment.
- **shouldAttachInvoiceToEarlyClosureEmailsWhenProcessingJob** — Regression test to ensure the email job service unconditionally includes the invoice attachment for early closure path emails.

## AI Confidence Scores
Plan: 85%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._