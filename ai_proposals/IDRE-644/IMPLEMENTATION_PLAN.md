## IDRE-644: Attorney: Search bar is no longer working

**Jira Ticket:** [IDRE-644](https://orchidsoftware.atlassian.net//browse/IDRE-644)

## Summary
This plan addresses a bug where the case search bar is not working for users with the 'Attorney' role. The fix involves updating the backend search API at `app/api/cases/search/route.ts` to correctly build the database query for attorneys, ensuring it filters for cases associated with their organization. No frontend changes are anticipated as the issue lies within the backend data fetching logic.

## Implementation Plan

**Step 1: Update Case Search API to Handle Attorney Role**  
In the `GET` function within `app/api/cases/search/route.ts`, locate the Prisma query that fetches case data. The current implementation does not correctly filter cases for users with the 'Attorney' role. You will need to add logic to check if the user's role is 'Attorney'. If it is, modify the `where` clause of the Prisma query to include cases where the attorney's associated organization is either the initiating or non-initiating party. This will likely involve using the `organizationId` from the user's session data to filter the results.
Files: `app/api/cases/search/route.ts`

**Risk Level:** LOW — The change is isolated to the case search API endpoint and is gated by a role check for 'Attorney'. This ensures that the search functionality for other roles like 'master admin' remains unaffected. The fix involves adding a condition to a database query, not altering core business logic or data schemas.

## Proposed Code Changes

### `app/api/cases/search/route.ts` (modify)
The previous implementation did not apply any organization-level filtering for the 'Attorney' role, causing the search to return no results or incorrect results. This change introduces a conditional block that checks if the user is an 'Attorney'. If so, it modifies the Prisma query to ensure that search results are limited to cases where the attorney's organization is either the initiating or non-initiating party. This is achieved by wrapping the existing search logic in an `AND` clause that also checks the `initiatingPartyId` and `nonInitiatingPartyId` against the user's `organizationId` from the session.
```typescript
--- a/app/api/cases/search/route.ts
+++ b/app/api/cases/search/route.ts
@@ -102,36 +102,46 @@
 
     const _queryT0 = performance.now();
 
+    // Base query for MasterAdmin and Support roles
+    let whereClause: any = {
+      OR: [
+        {
+          disputeReferenceNumber: {
+            contains: refSearchTerm,
+            mode: "insensitive",
+          },
+        },
+        {
+          initiatingParty: {
+            name: {
+              contains: searchTerm,
+              mode: "insensitive",
+            },
+          },
+        },
+        {
+          nonInitiatingParty: {
+            name: {
+              contains: searchTerm,
+              mode: "insensitive",
+            },
+          },
+        },
+      ],
+    };
+
+    // For Attorney role, scope the search to their organization
+    if (role === "Attorney" && session.user.organizationId) {
+      whereClause = {
+        AND: [
+          {
+            OR: [
+              { initiatingPartyId: session.user.organizationId },
+              { nonInitiatingPartyId: session.user.organizationId },
+            ],
+          },
+          whereClause,
+        ],
+      };
+    }
+
     const cases = await prisma.case.findMany({
-      where: {
-        OR: [
-          {
-            disputeReferenceNumber: {
-              contains: refSearchTerm,
-              mode: "insensitive",
-            },
-          },
-          {
-            initiatingParty: {
-              name: {
-                contains: searchTerm,
-                mode: "insensitive",
-              },
-            },
-          },
-          {
-            nonInitiatingParty: {
-              name: {
-                contains: searchTerm,
-                mode: "insensitive",
-              },
-            },
-          },
-        ],
-      },
+      where: whereClause,
       select: caseSelect,
       take: SEARCH_LIMIT,
       orderBy: {
```

**New Dependencies:**
- `_No new dependencies needed._`

## Test Suggestions

Framework: `Jest / Vitest`

- **shouldFilterSearchResultsByAttorneyOrganizationId** — This is the primary regression test to verify the bug fix. It ensures that when a logged-in attorney performs a search, the underlying database query is correctly filtered to only include cases associated with their organization.
- **shouldNotFilterSearchResultsForNonAttorneyRoles** — This test ensures that the fix for the 'Attorney' role did not inadvertently affect the search functionality for other roles, like 'Master Admin', who should have an unfiltered view of the cases matching the search term.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This document is the Product Requirements Document (PRD) for the Organization Management System. It is the most likely source for business rules and functional specifications detailing how the organization search should work, including specific permissions and expected behavior for different user roles like the 'Attorney' role mentioned in the ticket.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._