## IDRE-633: Party Portal: Sub Organization users having access to main organization bank account

**Jira Ticket:** [IDRE-633](https://orchidsoftware.atlassian.net//browse/IDRE-633)

## Summary
This plan addresses the security flaw where sub-organization users can access the main organization's bank accounts. The fix involves a targeted change to the `getPartyUserBankAccounts` server action. I will update this function to strictly filter bank accounts based on the user's direct organization memberships, preventing the inclusion of accounts from any parent organizations. This single backend change will correct the data displayed on both the payments and banking pages in the party portal.

## Implementation Plan

**Step 1: Update `getPartyUserBankAccounts` to filter by user's direct organization**  
Locate the `getPartyUserBankAccounts` server action, which is imported in `app/app/payments/page.tsx`. Modify its implementation to ensure it only fetches bank accounts strictly associated with the user's direct organization(s). The current logic incorrectly includes bank accounts from parent organizations. The updated logic should first retrieve the current user's organization memberships and then use those specific `organizationId`s in the `where` clause of the Prisma query for `PaymentBankInfo`. Do not traverse the organization hierarchy to include parent accounts.
Files: `lib/party-actions.ts`

**Risk Level:** MEDIUM — The change affects payment-related data fetching. An incorrect modification could prevent users from accessing their legitimate bank accounts or fail to resolve the access issue. The Confluence documentation highlights that the payments module is a "complexity hotspot," warranting careful testing across different organization structures (main orgs, sub-orgs) to ensure correctness.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
The previous implementation incorrectly fetched bank accounts for a user's entire organization hierarchy, including parent organizations. This allowed users in sub-organizations to see sensitive banking information from their parent organization.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -1,78 +1,69 @@
 "use server";
 
 import { unstable_cache } from "next/cache";
+import { getCurrentSession } from "@/lib/auth/utils";
 import { prisma } from "@/lib/prisma";
 import { PartyUserBankAccount } from "@/lib/types";
 
-async function getOrganizationHierarchy(organizationId: string): Promise<string[]> {
-  const orgs = [organizationId];
-  let currentOrgId: string | null = organizationId;
-
-  while (currentOrgId) {
-    const org = await prisma.organization.findUnique({
-      where: { id: currentOrgId },
-      select: { parentOrganizationId: true },
-    });
-    currentOrgId = org?.parentOrganizationId ?? null;
-    if (currentOrgId) {
-      orgs.push(currentOrgId);
-    }
-  }
-  return orgs;
-}
-
 export const getPartyUserBankAccounts = unstable_cache(
   async (
     partyUserId: string,
     organizationId?: string | null
   ): Promise<PartyUserBankAccount[]> => {
-    const user = await prisma.partyUser.findUnique({
-      where: { id: partyUserId },
-      include: {
-        organizationMemberships: {
-          select: {
-            organizationId: true,
-          },
-        },
-      },
-    });
+    const session = await getCurrentSession();
 
-    if (!user) {
+    // Validate session and ensure the user is the one making the request
+    if (
+      !session ||
+      session.user.id !== partyUserId ||
+      session.user.role !== "party" ||
+      !session.user.organizationMemberships
+    ) {
       return [];
     }
 
-    let orgIds: string[] = [];
-    if (organizationId) {
-      orgIds = await getOrganizationHierarchy(organizationId);
-    } else {
-      const allHierarchies = await Promise.all(
-        user.organizationMemberships.map((mem) =>
-          getOrganizationHierarchy(mem.organizationId)
-        )
-      );
-      orgIds = [...new Set(allHierarchies.flat())];
+    const userOrganizationIds = session.user.organizationMemberships.map(
+      (mem) => mem.organiz
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Vitest`

- **shouldNotReturnParentOrganizationBankAccountsForSubOrgUser** — This is the primary regression test. It simulates the exact scenario described in the ticket to ensure a user in a sub-organization cannot access the bank accounts of their parent organization.
- **shouldReturnCorrectBankAccountsForMainOrgUser** — This happy path test ensures that the fix does not break the existing, correct functionality for users who are direct members of an organization.
- **shouldReturnEmptyArrayForUserWithNoOrganization** *(edge case)* — This edge case handles users who might exist in the system but are not properly configured with an organization, preventing potential runtime errors.
- **shouldReturnAccountsForUserInMultipleDirectOrgs** *(edge case)* — This edge case ensures the logic correctly handles users with multiple direct memberships, aggregating data as expected.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the core requirements document for the feature in question. It should contain the definitive business rules regarding user permissions within the parent/sub-organization hierarchy, which is the central issue in the ticket.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page provides critical context, identifying the "Banking" and "Payments & Refunds Logic" as a major complexity hotspot prone to production issues. This informs the developer that the area of code is sensitive and requires careful testing.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be updated to explicitly state the access control rules regarding sub-organization users and parent-organization financial data. Adding a clear statement that sub-organization users are prohibited from accessing the parent's bank accounts will solidify the business requirement.

## AI Confidence Scores
Plan: 80%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._