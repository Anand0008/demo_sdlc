## IDRE-501: Email: Ineligible / Dismissal  

**Jira Ticket:** [IDRE-501](https://orchidsoftware.atlassian.net//browse/IDRE-501)

## Summary
This plan updates the email notification system to send a consistent "Ineligible / Dismissal" email. The core change involves modifying the `executeIneligiblePaymentWorkflow` function in `lib/actions/email-workflow.ts`. This function, triggered when a case is directly marked as ineligible, will be updated to send the same email template (`idr-dispute-not-eligible`) that is already used for cases marked as ineligible or dismissed through the administrative closure process. This ensures a uniform notification, including the correct email subject, body, and invoice attachment for the admin fee, across all ineligibility scenarios as required by the ticket.

## Implementation Plan

**Step 1: Update `executeIneligiblePaymentWorkflow` to Send 'Dispute Not Eligible' Email**  
In `lib/actions/email-workflow.ts`, locate the `executeIneligiblePaymentWorkflow` function. This function is triggered when a case status changes to `INELIGIBLE_PENDING_ADMIN_FEE`. Modify this function to send the 'Dispute Not Eligible' email (template `idr-dispute-not-eligible`) instead of the current admin fee request email. This involves replicating the logic from the `sendAdministrativeClosureEmailsInternal` function for `isIneligibilityCase`. This includes preparing the `ineligibilityTemplateData`, constructing the subject "The Federal IDR Process is Not Applicable to This Dispute - {disputeReferenceNumber}", handling invoice attachments for the admin fee, and using `createIDRProcessEmailJob` to send the email. The `reason` parameter passed to the function should be used as the `ineligibilityReason` in the template data.
Files: `lib/actions/email-workflow.ts`

**Risk Level:** LOW — The change is confined to a single server action responsible for email workflows. The logic being implemented is being adapted from an existing, similar workflow within the same file, reducing the risk of introducing new bugs. The primary risk is ensuring all necessary data for the email template and invoice generation is correctly fetched and passed, but this is mitigated by following the existing pattern.

## Proposed Code Changes

### `lib/actions/email-workflow.ts` (modify)
The `executeIneligiblePaymentWorkflow` function is updated to align with the email logic used for administrative closures (`sendAdministrativeClosureEmailsInternal`). Previously, it sent a notification to an internal-only email address. This change modifies it to:
1.  Send the "Dispute Not Eligible" email directly to the initiating and non-initiating parties.
2.  Use `createIDRProcessEmailJob` for consistency with other process-related emails.
3.  Attach party-specific invoices to each email, rather than bundling all invoices into a single internal email.
4.  Adopt the standardized template data and subject line used for ineligibility and dismissal notifications.
```typescript
--- a/lib/actions/email-workflow.ts
+++ b/lib/actions/email-workflow.ts
@@ -2528,93 +2528,102 @@
     }
 
     if (
-      !caseData.initiatingParty?.email ||
-      !caseData.nonInitiatingParty?.email
+      !caseData.initiatingParty?.email || !caseData.initiatingParty?.name ||
+      !caseData.nonInitiatingParty?.email || !caseData.nonInitiatingParty?.name
     ) {
       return {
         success: false,
-        error: "Case parties must have email addresses",
+        error: "Case parties must have names and email addresses",
       };
     }
 
-    // Prepare template data for ineligible case using Template 9 (Dispute Not Eligible)
-    const templateData = prepareIDRPaymentTemplateData(
-      caseData,
-      data.customPaymentInstructions,
-      false // Don't include dispute details for ineligible cases
-    );
-
-    // Add ineligibility reason, status, and early closure reason to template data
-    // Only set disputeStatus for standard ineligibility cases, not early closures
-    if (!data.earlyClosureReason) {
-      templateData.disputeStatus = caseData.status === "INELIGIBLE" ? "Not eligible" : "Not eligible - pending admin fee";
-    }
-    templateData.ineligibilityReason =
-      data.reason ||
-      "the dispute does not meet the eligibility criteria for the Federal IDR process";
-    templateData.earlyClosureReason = data.earlyClosureReason;
-
-    // Ineligibility emails are restricted to the NSA inbox only
-    const NSA_EMAIL = "federalnsa@capitolbridge.com";
-    const recipients = [NSA_EMAIL];
+    // Prepare template data for ineligibility/dismissal (Template 9)
+    const ineligibilitySubject = `The Federal IDR Process is Not Applicable to This Dispute - ${caseData.disputeReferenceNumber}`;
+    const ineligibilityTemplateData = {
+      disputeReferenceNumber: caseData.disputeReferenceNumber,
+      caseId: data.caseId,
+      disputeStatus: "Not eligible",
+      ineligibilityReason:
+        data.reason ||
+        "the dispute does 
... (truncated — see full diff in files)
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Vitest`

- **shouldSendIneligibleEmailToBothPartiesWithTheirRespectiveInvoices** — This test verifies the primary success path where a dispute is marked ineligible, and both parties have valid emails and invoices. It ensures the correct email job is created for each party with their respective invoice attached.
- **shouldSendEmailWithoutAttachmentIfPartyHasNoInvoice** *(edge case)* — This test covers the scenario where an invoice might not have been generated for one of the parties. It ensures that the email is still sent, but without an attachment.
- **shouldNotAttemptToSendEmailToPartyWithMissingEmailAddress** *(edge case)* — This test ensures the function handles missing party contact information gracefully and does not attempt to send an email to a null address, which could cause an error.

## Confluence Documentation References

- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This page provides the most critical business logic for the ticket. It defines the exact status `INELIGIBLE_PENDING_ADMIN_FEE`, confirms the $115 admin fee is collected from the Initiating Party (IP), and explicitly states this fee is never refunded. This directly informs the content of the email and the reason for the attached invoice.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This document establishes the high-level business process where a case is marked 'Ineligible' during the Eligibility Review phase. It confirms that a notification is sent to both parties with the closure reason, which is the core requirement of the ticket.
- [IDRE Stand up Notes](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/206602242) — This page provides direct context for the developer. It explicitly mentions ticket IDRE-501 and a technical issue where emails were not being sent correctly in the staging environment. It also references the parent ticket, IDRE-354, indicating its priority.
- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This page highlights two other active tickets that are highly relevant to the scope of IDRE-501. 'IDRE-530' indicates known issues with invoicing for ineligible disputes, and 'IDRE-508' shows an existing requirement to include invoices in payment-related emails. This context is crucial for the developer to avoid conflicts and understand the technical landscape.

**Suggested Documentation Updates:**

- IDRE Case Workflow Documentation
- IDRE Worflow

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._