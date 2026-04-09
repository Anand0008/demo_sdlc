## IDRE-603: User is not able to search newly created organization under Org Reconciliation page

**Jira Ticket:** [IDRE-603](https://orchidsoftware.atlassian.net//browse/IDRE-603)

## Summary
Fix organization search to be case-insensitive across server actions and API routes, ensuring newly created organizations can be found regardless of the search input casing.

## Implementation Plan

**Step 1: Make server actions search case-insensitive**  
Update the Prisma `findMany` queries in both `searchOrganizations` and `getOrganizations` functions. Modify the `where` clause for the `name` field to include `mode: "insensitive"` alongside the `contains` operator (e.g., `name: { contains: trimmed, mode: "insensitive" }`). This ensures searches match newly created organizations regardless of case.
Files: `lib/actions/organization.ts`

**Step 2: Make API route search case-insensitive and verify caching**  
Locate the Prisma query that filters organizations by the `rawQuery` search parameter. Update the `name: { contains: rawQuery }` condition to include `mode: "insensitive"`. Additionally, ensure the route is not being statically cached by verifying dynamic functions are used or explicitly adding `export const dynamic = "force-dynamic";` if necessary.
Files: `app/api/organizations/search/route.ts`

**Risk Level:** LOW — The changes are isolated to adding a case-insensitivity flag to existing Prisma queries. This is a standard, low-risk modification that will strictly improve search recall without affecting other system behaviors.

**Deployment Notes:**
- No special deployment steps required. The fix only modifies application-level query parameters.

## Proposed Code Changes

### `lib/actions/organization.ts` (modify)
Adding `mode: "insensitive"` to the Prisma `contains` filter ensures that searches match organizations regardless of case, fixing the issue where newly created organizations couldn't be found if the casing didn't match exactly.
```typescript
--- a/lib/actions/organization.ts
+++ b/lib/actions/organization.ts
@@ -20,7 +20,7 @@
     const session = await auth.api.getSession({ headers: await headers() });
     if (!session) return { success: false, error: "Authentication required" };
     const trimmed = query.trim();
     const organizations = await prisma.organization.findMany({
-      where: trimmed ? { name: { contains: trimmed } } : undefined,
+      where: trimmed ? { name: { contains: trimmed, mode: "insensitive" } } : undefined,
       select: { id: true, name: true, type: true, email: true },
       orderBy: { name: "asc" },
       take: 50,
@@ -52,7 +52,7 @@
     const take = options?.take ?? 50;
     const skip = options?.skip ?? 0;
     const search = options?.search?.trim();
 
-    const where = search ? { name: { contains: search } } : undefined;
+    const where = search ? { name: { contains: search, mode: "insensitive" } } : undefined;
 
     // Fetch one extra to determine if there are more results
     const organ
```

### `app/api/organizations/search/route.ts` (modify)
Adding `export const dynamic = "force-dynamic";` ensures the route is never statically cached, which could cause stale search results. Adding `mode: "insensitive"` to the search query ensures case-insensitive matching for the API route as well.
```typescript
--- a/app/api/organizations/search/route.ts
+++ b/app/api/organizations/search/route.ts
@@ -6,6 +6,8 @@
 import { OrganizationType } from "@prisma/client";
 import { posthogClient } from "@/lib/posthog/server";
 
+export const dynamic = "force-dynamic";
+
 const MIN_QUERY_LENGTH = 2;
 
 interface OrganizationSearchResult {
@@ -100,7 +102,7 @@
-          name: { contains: rawQuery }
+          name: { contains: rawQuery, mode: "insensitive" }
```

## Test Suggestions

Framework: `Jest`

- **should search organizations case-insensitively** — Verifies that the Prisma query includes mode: 'insensitive' to fix the bug where newly created orgs with different casing were not found.
- **should handle case-insensitive search via API route** — Verifies that the API route passes mode: 'insensitive' to Prisma and handles the search query correctly.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — Contains the product requirements for the Organization Management System, which dictates how organizations are created, stored, and managed within the platform.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — Provides an overview of the Organization Management and Admin Tools, which encompasses the administrative interfaces like the Org Reconciliation page.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — Outlines the QA workflow for testing organization creation and selection, which is directly related to the bug's domain.

**Suggested Documentation Updates:**

- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: Needs to be updated to include a specific test case verifying that newly created organizations are immediately searchable on the Org Reconciliation page.
- Product Requirements Document for IDRE Dispute Platform's Organization Management System: May need an update to explicitly define the expected search visibility SLA (e.g., real-time vs. eventual consistency) for newly created organizations.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._