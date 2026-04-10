## IDRE-501: Email: Ineligible / Dismissal  

**Jira Ticket:** [IDRE-501](https://orchidsoftware.atlassian.net//browse/IDRE-501)

## Summary
Implement the Ineligible/Dismissal email notification by adding the required template to the existing email button component and integrating it into the invoice details view to ensure the invoice is attached.

## Implementation Plan

**Step 1: Add Ineligible/Dismissal Email Template**  
Update the component to support a new email type for 'Ineligible/Dismissal'. Add the email subject ('The Federal IDR Process is Not Applicable to This Dispute - DISP-[IDR]') and the provided body template. Ensure the template interpolates the IDR reference number and the ineligibility/dismissal reason. Configure the email payload to attach the associated invoice PDF.
Files: `components/email/send-payment-email-button.tsx`

**Step 2: Integrate Email Button in Invoice View**  
Update the invoice details view to conditionally render the `SendPaymentEmailButton` configured for the new 'Ineligible/Dismissal' email type when the associated case is marked as ineligible or dismissed. Extract the IDR reference number and the reason from the case data and pass them as props to the button.
Files: `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx`

**Risk Level:** LOW — The changes are confined to the frontend email button component and the invoice details view, utilizing existing email sending patterns without altering core backend logic.

**Deployment Notes:**
- Ensure the email service is configured to handle the new template and attachments correctly.

## Proposed Code Changes

### `components/email/send-payment-email-button.tsx` (modify)
Added the new email type `ineligible_dismissal` to the button props and implemented the email subject and body template as specified in the ticket. The template interpolates the IDR reference number and the reason for ineligibility/dismissal.
```
--- a/components/email/send-payment-email-button.tsx
+++ b/components/email/send-payment-email-button.tsx
@@ -10,7 +10,9 @@
 export interface SendPaymentEmailButtonProps {
   invoiceId: string;
-  emailType: 'payment_receipt' | 'invoice_reminder';
+  emailType: 'payment_receipt' | 'invoice_reminder' | 'ineligible_dismissal';
   recipientEmail?: string;
+  referenceNumber?: string;
+  reason?: string;
 }
 
 export function SendPaymentEmailButton({
   invoiceId,
   emailType,
   recipientEmail,
+  referenceNumber,
+  reason,
 }: SendPaymentEmailButtonProps) {
@@ -45,6 +47,38 @@
       body = `...`;
       break;
+    case 'ineligible_dismissal':
+      subject = `The Federal IDR Process is Not Applicable to This Dispute - ${referenceNumber || 'DISP-XXXXXX'}`;
+      body = `**IDR dispute status:** Not eligible
+**IDR reference number:** ${referenceNumber || 'DISP-XXXXXX'}
+
+Capitol Bridge has reviewed your Independent Dispute Resolution (IDR) reference number ${referenceNumber || 'DISP-XXXXXX'} and determined that the dispute is not eligible to be resolved using the Federal IDR process for the following reason(s): 
+- **${reason || 'Open negotiations not completed.'}**
+
+Your Federal IDR dispute with reference number ${referenceNumber || 'DISP-XXXXXX'} has been closed. Keep this notice and your IDR reference number for your records. 
+
+If you believe you have received this notice in error, please contact us immediately at [EMAIL REDACTED]. Include your IDR reference number above.
+
+**Next Steps:** 
+There is one fee associated with this dispute:
+- The administrative fee, $115.00. 
+
+An invoice for the outstanding administrative fee ($115) can be populated by logging in our secure portal. Payment is due upon receipt of this email. You may submit payment through our secure portal at https://app.veratru.com by logging in using the email address this message was sent to for streamlined payment. Alternatively, you can pay using the instructions provided on the invoic
... (truncated — see full diff in files)
```

### `app/app/invoices/[invoiceId]/components/invoice-details-view.tsx` (modify)
Conditionally render the `SendPaymentEmailButton` configured for the new 'Ineligible/Dismissal' email type when the associated case is marked as ineligible or dismissed. Extracted the IDR reference number and the reason from the case data and passed them as props to the button.
```
--- a/app/app/invoices/[invoiceId]/components/invoice-details-view.tsx
+++ b/app/app/invoices/[invoiceId]/components/invoice-details-view.tsx
@@ -50,6 +50,15 @@
           <SendPaymentEmailButton
             invoiceId={invoice.id}
             emailType="invoice_reminder"
             recipientEmail={invoice.recipientEmail}
           />
+          {(invoice.case?.status === 'INELIGIBLE' || invoice.case?.status === 'DISMISSED') && (
+            <SendPaymentEmailButton
+              invoiceId={invoice.id}
+              emailType="ineligible_dismissal"
+              recipientEmail={invoice.recipientEmail}
+              referenceNumber={invoice.case?.referenceNumber}
+              reason={invoice.case?.ineligibilityReason || invoice.case?.dismissalReason}
+            />
+          )}
         </div>
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest/Vitest with React Testing Library`

- **shouldGenerateCorrectEmailPayloadForIneligibleDismissalType** — Verifies that the email template correctly interpolates the IDR reference number and reason for the ineligible/dismissal email type.
- **shouldRenderEmailButtonWhenCaseIsIneligible** — Ensures the email button is visible when the case is ineligible or dismissed.
- **shouldNotRenderIneligibleEmailButtonWhenCaseIsActive** *(edge case)* — Ensures the ineligible/dismissal email button is hidden for active cases to prevent accidental sends.

## AI Confidence Scores
Plan: 60%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._