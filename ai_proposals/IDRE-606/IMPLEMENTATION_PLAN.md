## IDRE-606: When user has configured same bank account under organization has both saving and refund account able to see Set as Refund option in Organization Reconciliation page

**Jira Ticket:** [IDRE-606](https://orchidsoftware.atlassian.net//browse/IDRE-606)

## Summary
This plan corrects a UI bug where the "Set as Refund" option is incorrectly displayed for a bank account that is already the designated refund account. The fix involves updating the `getUserBankAccounts` server action in `lib/party-actions.ts` to fetch the refund bank account ID from the correct `organization` model in the database, rather than the `user` model. This ensures the UI receives accurate data and correctly hides the redundant "Set as Refund" option.

## Implementation Plan

**Step 1: Correct refund account data fetching in `getUserBankAccounts`**  
In `lib/party-actions.ts`, modify the `getUserBankAccounts` function to fetch the `refundPayoutBankAccountId` from the `organization` model instead of the `user` model. Replace the raw SQL query at lines 1016-1020 with a Prisma query to find the organization using `membership.organizationId`. Then, use the `refundPayoutBankAccountId` from the fetched organization object when constructing the `transformedUser` object. This can be done efficiently using `Promise.all` to fetch both the organization data and the list of bank accounts concurrently.
Files: `lib/party-actions.ts`

**Risk Level:** LOW — The change is a targeted fix to a data-fetching function, correcting a query to align with the database schema. The function `setRefundAccount` already correctly writes to the organization model; this change brings the read logic in line with the existing write logic, ensuring data consistency. The scope is limited to a single function, minimizing the risk of unintended side effects.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
The original code was incorrectly querying the `user` table for the `refundPayoutBankAccountId`, which is a field on the `organization` table. This change corrects the data source by fetching the user's organization and using its `refundPayoutBankAccountId`, ensuring the UI receives the correct data to determine if a bank account is already the designated refund account. Using `Promise.all` also improves performance by fetching user, organization, and bank account data concurrently.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -988,50 +988,56 @@
       };
     }
 
-    const user = await prisma.user.findUnique({
-      where: {
-        id: session.user.id,
-      },
-    });
-
-    // Get user's organization bank accounts
+    // Get user's organization ID first
     const membership = await prisma.member.findFirst({
       where: { userId: session.user.id },
       select: { organizationId: true },
     });
 
     if (!membership?.organizationId) {
       throw new Error("Party user must belong to an organization");
     }
 
-    const bankAccounts = await prisma.bankAccount.findMany({
-      where: {
-        organizationId: membership.organizationId,
-        isActive: true,
-      },
-      orderBy: {
-        createdAt: "desc",
-      },
-    });
-
-    // Get refund account ID using raw SQL temporarily
-    const refundAccountResult = await prisma.$queryRaw<
-      Array<{ refundPayoutBankAccountId: string | null }>
-    >`
-      SELECT refundPayoutBankAccountId FROM user WHERE id = ${session.user.id}
-    `;
+    const [user, organization, bankAccounts] = await Promise.all([
+      prisma.user.findUnique({
+        where: { id: session.user.id },
+        select: { id: true, name: true, email: true },
+      }),
+      prisma.organization.findUnique({
+        where: { id: membership.organizationId },
+        select: { refundPayoutBankAccountId: true },
+      }),
+      prisma.bankAccount.findMany({
+        where: {
+          organizationId: membership.organizationId,
+          isActive: true,
+        },
+        orderBy: {
+          createdAt: "desc",
+        },
+      }),
+    ]);
 
     if (!user) {
       return {
         success: false,
         error: "User not found",
       };
     }
 
+    if (!organization) {
+      return {
+        success: false,
+        error: "Organization not found",
+      };
+    }
+
     // Transform the user data to match the expected type
     // SECURITY: Remove sensitive fie
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldCorrectlyIdentifyTheRefundAccount** — This test validates the primary fix by ensuring that when a bank account is already set as the organization's refund account, it is correctly identified in the data returned by the server action. This prevents the UI from incorrectly showing the 'Set as Refund' option.
- **shouldNotFlagAnyAccountAsRefundWhenNoneIsSet** *(edge case)* — This test covers the scenario where an organization has not yet designated a refund account. It ensures that no account is incorrectly flagged as the refund account.
- **shouldThrowErrorWhenUserIsNotFound** *(edge case)* — This test ensures the function handles cases where the user cannot be found, preventing downstream errors.
- **shouldThrowErrorWhenOrganizationIsNotFound** *(edge case)* — This test handles a data integrity issue where a user might be orphaned from their organization.

## Confluence Documentation References

- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document is the user-facing guide for the "Organization Reconciliation" tool, which is the exact location of the bug described in ticket IDRE-606. It confirms that banking information is managed within this tool, providing essential context for the UI change.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This Product Requirements Document (PRD) is the foundational document defining the Organization Management system. It explicitly names the "Organization Reconciliation" tool and outlines the business requirements for "Banking Account Binding," which are central to the ticket.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document provides critical context by identifying "Banking & Banking Dashboard Issues" as a major pain point. It specifically calls out the need for QA focus on "Separate default and refund accounts," which is the core issue in the ticket. This highlights the sensitivity of the feature area for the developer.

**Suggested Documentation Updates:**

- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview - The document contains screenshots and descriptions of the Organization Reconciliation tool. These may need to be updated to reflect the corrected UI where the "Set as Refund" option is no longer shown for accounts that are already configured for refunds.
- Product Requirements Document for IDRE Dispute Platform's Organization Management System - As the source of truth for requirements, this PRD could be updated to explicitly state the business rule that the "Set as Refund" option should be hidden or disabled if a bank account already serves as both the default and refund account, to prevent future implementation ambiguity.

## AI Confidence Scores
Plan: 100%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._