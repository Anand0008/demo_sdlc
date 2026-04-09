## IDRE-620: Not able to see newly created case under cases tab of suborganizations

**Jira Ticket:** [IDRE-620](https://orchidsoftware.atlassian.net//browse/IDRE-620)

## Summary
Fix the visibility of newly created cases in suborganizations by ensuring the selected suborganization ID is correctly passed and used for filtering in the cases page, client component, and search API.

## Implementation Plan

**Step 1: Use selected suborganization ID for fetching cases**  
Update the server-side data fetching logic to extract the active organization ID (e.g., from `searchParams` or cookies) representing the selected suborganization. Pass this specific ID to the case fetching function instead of defaulting to the user's primary organization, ensuring newly created cases for the suborganization are retrieved.
Files: `app/app/cases/page.tsx`

**Step 2: Preserve organization context in client-side actions**  
Modify the client-side component to ensure that `currentOrganizationId` is preserved and included in all URL updates or API requests triggered by pagination, filtering, or searching. This prevents the view from resetting to the main organization when interacting with the cases list.
Files: `app/app/cases/components/cases-page-client.tsx`

**Step 3: Filter search results by suborganization ID**  
Update the GET handler to accept an `organizationId` query parameter. Apply this ID in the Prisma query's `where` clause (checking both `initiatingPartyId` and `nonInitiatingPartyId` or the relevant organization relation) to ensure search results are correctly scoped to the selected suborganization.
Files: `app/api/cases/search/route.ts`

**Risk Level:** LOW — The changes are isolated to the cases list and search filtering logic in the party portal. By explicitly passing and filtering by the selected organization ID, we avoid impacting the broader case management system while fixing the visibility issue for suborganizations.

**Deployment Notes:**
- Ensure that users with access to suborganizations have the correct permissions to view cases assigned to those suborganizations.

## Proposed Code Changes

### `app/api/cases/search/route.ts` (modify)
Extracts the `organizationId` from the search parameters and applies it to the Prisma query's `where` clause to ensure search results are correctly scoped to the selected suborganization.
```typescript
--- a/app/api/cases/search/route.ts
+++ b/app/api/cases/search/route.ts
@@ -46,6 +46,7 @@
 
     const { searchParams } = new URL(request.url);
     const query = searchParams.get("q");
+    const organizationId = searchParams.get("organizationId");
 
     if (!query || query.trim().length < 2) {
       return NextResponse.json({
@@ -62,9 +63,22 @@
       /^\d+$/.test(searchTerm) ? `${refPrefix}${searchTerm}` : null;
     const refSearchTerm = normalizedRefTerm ?? searchTerm;
 
+    const orgFilter = organizationId
+      ? {
+          AND: [
+            {
+              OR: [
+                { initiatingPartyId: organizationId },
+                { nonInitiatingPartyId: organizationId },
+              ],
+            },
+          ],
+        }
+      : {};
+
     const _queryT0 = performance.now();
     const cases = await prisma.case.findMany({
       where: {
+        ...orgFilter,
         OR: [
```

### `app/app/cases/page.tsx` (modify)
Updates the server-side data fetching logic to extract the active organization ID from `searchParams` (representing the selected suborganization) instead of defaulting to the user's primary organization.
```
--- a/app/app/cases/page.tsx
+++ b/app/app/cases/page.tsx
@@ -20,7 +20,8 @@
   if (!session) {
     redirect("/login");
   }
 
-  const organizationId = session.user.organizationId;
+  const resolvedSearchParams = await searchParams;
+  const organizationId = (resolvedSearchParams?.organizationId as string) || session.user.organizationId;
 
   // Fetch cases
```

### `app/app/cases/components/cases-page-client.tsx` (modify)
Ensures that `currentOrganizationId` is preserved and included in all URL updates triggered by
```
--- a/app/app/cases/components/cases-page-client.tsx
+++ b/app/app/cases/components/cases-page-client.tsx
@@ -45,6 +45,10 @@
         if (value === null) {
           params.delete(key);
         } else {
           params.set(key, value);
         }
       });
 
+      if (currentOrganizationId) {
+        params.set("organizationId", currentOrganizationId);
+      }
+
       router.push(`${pathname}?${params.toString()}`);
     },
     [pathname, router, searchParams, currentOrganizationId]
```

## Test Suggestions

Framework: `Jest or Vitest with React Testing Library`

- **should filter cases by organizationId when provided in search parameters** — Verifies that the search API correctly extracts the organizationId from the query parameters and applies it to the database query, fixing the bug where suborganization cases were not returned.
- **should fetch cases using organizationId from searchParams instead of primary organization** — Ensures the server component correctly reads the active organization ID from searchParams to fetch the correct suborganization cases on initial load.
- **should preserve currentOrganizationId in URL when updating search filters** — Verifies that client-side navigation and filtering do not drop the suborganization context, preventing the user from accidentally reverting to their primary organization\'s cases.

## AI Confidence Scores
Plan: 75%, Code: 90%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._