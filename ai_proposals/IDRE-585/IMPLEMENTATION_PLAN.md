## IDRE-585: Invoice Issues

**Jira Ticket:** [IDRE-585](https://orchidsoftware.atlassian.net//browse/IDRE-585)

## Summary
This plan fixes a bug where creating or deleting an invoice does not consistently update the list of disputes awaiting payment. The root cause is incomplete cache invalidation; while the page data is refreshed, the cached overview statistics (like pending case counts) are not.

The fix involves adding a specific cache revalidation call (`revalidatePartyPaymentOverview`) to two server actions:
1.  `createInvoiceFromCases`: To update stats after an invoice is created.
2.  `deletePendingInvoice`: To update stats after an invoice is deleted.

These changes will ensure that both the list of cases and the summary counts on the payments page are synchronized, resolving the inconsistency reported in the ticket.

## Implementation Plan

**Step 1: Update Invoice Creation to Revalidate Payment Overview Cache**  
In the `createInvoiceFromCases` function, import `revalidatePartyPaymentOverview` from `lib/payments/overview-cache.ts`. After the invoice is successfully created and existing paths are revalidated, add a call to `revalidatePartyPaymentOverview(session.user.id, invoiceOrganizationId)`. This will ensure that the cached payment overview statistics are invalidated when a new invoice is created, forcing the UI to refetch the correct counts.
Files: `lib/actions/party-dashboard.ts`

**Step 2: Update Invoice Deletion to Revalidate Payment Overview Cache**  
In the `deletePendingInvoice` function, import `revalidatePartyPaymentOverview` from `lib/payments/overview-cache.ts`. After the invoice is successfully deleted (after the `prisma.invoice.delete` call), add a call to `revalidatePartyPaymentOverview(session.user.id, invoice.organizationId)`. This will invalidate the cached payment overview statistics, ensuring the counts of pending cases and invoices are updated correctly when an invoice is deleted.
Files: `lib/actions/party-dashboard.ts`

**Risk Level:** LOW — The change is low-risk as it only involves adding cache invalidation calls to existing server actions. This is unlikely to have unintended side effects and directly targets the observed data inconsistency. The core logic for creating and deleting invoices remains untouched.

## Proposed Code Changes

### `lib/actions/party-dashboard.ts` (modify)
The ticket describes an inconsistency between the list of cases awaiting payment and the summary statistics after creating or deleting an invoice. This is due to incomplete cache invalidation.
```typescript
--- a/lib/actions/party-dashboard.ts
+++ b/lib/actions/party-dashboard.ts
@@ -34,6 +34,7 @@
   getPartyPaymentOverviewScopeTag,
   getPartyPaymentOverviewUserTag,
   PARTY_PAYMENT_OVERVIEW_CACHE_TTL_SECONDS,
+  revalidatePartyPaymentOverview,
 } from "@/lib/payments/overview-cache";
 
 /**
@@ -2377,6 +2378,8 @@
 
     const organizationNames = Array.from(organizationNamesForInvoice);
 
+    revalidatePartyPaymentOverview(session.user.id, invoiceOrganizationId);
+
     return {
       success: true,
       data: {
@@ -2623,6 +2626,8 @@
 
     await prisma.invoice.delete({ where: { id: invoiceId } });
 
+    revalidatePartyPaymentOverview(session.user.id, invoice.organizationId);
+
     // Revalidate paths so the invoice queue and payment tab reflect the change
     if (invoice.organizationId) {
       revalidatePath(`/dashboard/organizations/${invoice.organizationId}/financial`);
```

**New Dependencies:**
- `_No new dependencies needed_`

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page provides the canonical end-to-end case lifecycle, including the critical 'Payments' phase. The ticket is about fixing the logic of how disputes and invoices interact within this workflow, specifically how a dispute's status changes from 'Pending Payment' when an invoice is created or deleted. This document defines the correct state transitions.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — The ticket is a subtask of 'Organization Management' and deals with invoice/payment issues. This PRD explains that payment errors are a high-severity problem often caused by duplicate organization records. It provides critical architectural context, stating that banking information must be explicitly tied to a verified organization before payments can be processed. This informs the developer that any fix must align with this data integrity strategy.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document provides a thematic analysis of recurring bugs, highlighting that the 'Payments & Refunds Logic', 'Invoicing & Invoice Acknowledgement', and 'Organization & User Data Integrity' are all major 'pain points' and complexity hotspots. This is essential context for a developer, warning them that the area is fragile and that status transitions based on payments are a common source of production issues.
- [Proposed Changes to Address Current Issues](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/246906881) — This page contains meeting notes that explicitly list 'Invoice System Fixes' and 'Data Normalization Needed' as key initiatives. This confirms for the developer that the ticket is part of a recognized, broader effort to correct systemic issues in the invoicing and payment process, providing strategic context for the bug fix.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This document outlines the specific E2E testing workflow that QA uses to validate payment and invoice functionality. It describes the expected 'happy path' behavior, such as generating an invoice and confirming it appears in the 'Pending Invoice Acknowledgement' tab. This serves as a clear set of acceptance criteria for the developer's work.

**Suggested Documentation Updates:**

- IDRE Worflow: The ticket addresses the logic of how creating/deleting an invoice affects a dispute's status in the payment queue. This document outlines the canonical case lifecycle and status changes, and it should be updated to reflect the corrected, implemented behavior.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: This document's testing steps for the Payment & Party Portal will need to be updated to include specific checks for the behavior described in the ticket, such as verifying that deleting an invoice returns a dispute to the payment tab and that CSV and invoice downloads match.

## AI Confidence Scores
Plan: 90%, Code: 100%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._