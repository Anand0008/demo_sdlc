## IDRE-647: Adjust Member Count: Main Organization

**Jira Ticket:** [IDRE-647](https://orchidsoftware.atlassian.net//browse/IDRE-647)

## Summary
This plan addresses the need to adjust the member count for main organizations by de-duplicating users across sub-organizations. The core of the work involves modifying the `getOrganizations` server action in `lib/actions/organization.ts` to implement a more complex query that counts unique users. A verification step ensures the UI component, `components/organizations-management.tsx`, correctly displays the new count.

## Implementation Plan

**Step 1: Update `getOrganizations` to Count Unique Members Across Sub-Organizations**  
Modify the `getOrganizations` function to change how member counts are calculated for main organizations. Instead of a simple count of members, the new logic must count the number of unique users associated with the main organization and all of its sub-organizations. This will likely require a more complex query, potentially a `prisma.$queryRaw` statement, to efficiently fetch the list of organizations along with a de-duplicated member count. The query should look for members across the organization itself and any organization that lists it as a `parentOrganizationId`, then count the distinct `userId`s. The existing pagination and search functionality must be preserved within the new query logic.
Files: `lib/actions/organization.ts`

**Step 2: Verify UI Component Displays Correct Member Count**  
The `OrganizationsManagement` component, which is rendered by `app/dashboard/organizations/page.tsx`, is responsible for fetching and displaying the list of organizations. Verify that this component correctly consumes the updated data from the `getOrganizations` action. If the property name for the member count has changed in the action's return value, update the component to use the new property to display the correct, de-duplicated member count as shown in the screenshot.
Files: `components/organizations-management.tsx`

**Risk Level:** LOW — The primary risk is in the complexity of the database query needed to get the de-duplicated member count efficiently. A raw SQL query might be required, which adds a small risk if not constructed carefully to handle pagination and searching correctly. However, the change is confined to a single server action, limiting the potential blast radius.

## Proposed Code Changes

### `lib/actions/organization.ts` (modify)
The core requirement is to change how members are counted for main organizations. The previous implementation likely used a simple `prisma.organization.findMany` with a `_count` on members, which does not de-duplicate users across sub-organizations.
```typescript
--- a/lib/actions/organization.ts
+++ b/lib/actions/organization.ts
@@ -1,7 +1,7 @@
 "use server";
 
 import { auth } from "@/lib/auth/server";
-import { headers } from "next/headers";
+import { headers } from "next/headers";
 import { prisma } from "@/lib/database";
 import { OrganizationType } from "@prisma/client";
 
@@ -43,10 +43,16 @@
   search?: string;
   take?: number;
   skip?: number;
-}): Promise<ActionResult<{ items: Array<{ id: string; name: string; type: string }>; hasMore: boolean }>> {
+}): Promise<
+  ActionResult<{
+    items: Array<{ id: string; name: string; type: string; memberCount: number }>;
+    hasMore: boolean;
+  }>
+> {
   try {
     const session = await auth.api.getSession({
       headers: await headers(),
     });
 
     if (!session) {
@@ -58,32 +64,49 @@
 
     const take = options?.take ?? 50;
     const skip = options?.skip ?? 0;
-    const search = options?.search?.trim();
+    const search = options?.search?.trim() ?? "";
 
-    const where = search ? { name: { contains: search } } : undefined;
+    // Using a raw query to handle the conditional member count logic:
+    // - For main organizations (parent is null), count distinct users across the org and its sub-orgs.
+    // - For sub-organizations, count all members of that specific org.
+    const organizationsWithCount: Array<{
+      id: string;
+      name: string;
+      type: OrganizationType;
+      memberCount: bigint;
+    }> = await prisma.$queryRaw`
+      SELECT
+        o.id,
+        o.name,
+        o.type,
+        (
+          CASE
+            WHEN o."parentOrganizationId" IS NULL THEN (
+              SELECT COUNT(DISTINCT om."userId")
+              FROM "OrganizationMember" AS om
+              WHERE om."organizationId" = o.id OR om."organizationId" IN (
+                SELECT sub.id FROM "Organization" AS sub WHERE sub."parentOrganizationId" = o.id
+              )
+            )
+            ELSE (
+              SELECT COUNT(om."userId")
+            
... (truncated — see full diff in files)
```

### `components/organizations-management.tsx` (modify)
The `getOrganizations` action now returns a `memberCount` property instead of a nested `_count: { members: number }` object. This component, which consumes the data from that action, needs to be updated to use the new property.
```
--- a/components/organizations-management.tsx
+++ b/components/organizations-management.tsx
@@ -1,22 +1,22 @@
 "use client";
 
-import { getOrganizations } from "@/lib/actions";
+import { getOrganizations } from "@/lib/actions/organization";
 import { useInfiniteQuery } from "@tanstack/react-query";
 import { useEffect } from "react";
 import { useInView } from "react-intersection-observer";
 import { OrganizationCard, OrganizationCardSkeleton } from "./organizations/organization-card";
 import { useOrganizationSearch } from "@/lib/stores/organization-search-store";
 
-type Organization = Awaited<ReturnType<typeof getOrganizations>>["data"]["items"][number];
+type Organization = Awaited<ReturnType<typeof getOrganizations>>["data"]["items"][number] & {
+  memberCount: number;
+};
 
 export default function OrganizationsManagement() {
   const { searchTerm } = useOrganizationSearch();
   const { ref, inView } = useInView();
 
   const { data, fetchNextPage, hasNextPage, isFetchingNextPage, status } = useInfiniteQuery({
-    queryKey: ["organizations", searchTerm],
-    queryFn: async ({ pageParam = 0 }) => {
-      const res = await getOrganizations({ search: searchTerm, skip: pageParam, take: 10 });
-      if (!res.success) throw new Error(res.error);
-      return res.data;
-    },
+    queryKey: ["organizations", searchTerm],
+    queryFn: async ({ pageParam = 0 }) => {
+      const res = await getOrganizations({ search: searchTerm, skip: pageParam, take: 10 });
+      if (!res.success) throw new Error(res.error);
+      return res.data;
+    },
     initialPageParam: 0,
     getNextPageParam: (lastPage, allPages) => {
       return lastPage.hasMore ? allPages.length * 10 : undefined;
@@ -43,7 +43,7 @@
       {status === "success" &&
         data.pages.map((page) =>
           page.items.map((org: Organization) => (
-            <OrganizationCard key={org.id} name={org.name} members={org._count.members} type={org.type} />
+            <OrganizationCard key={org.id
... (truncated — see full diff in files)
```

**New Dependencies:**
- `_(none)_`

## Test Suggestions

Framework: `Vitest`

- **shouldReturnCorrectMemberCountWithOverlappingMembersInSubOrgs** — This test validates the core requirement of the ticket: that unique users across a main organization and its sub-organizations are counted only once.
- **shouldReturnCorrectMemberCountWithNoSubOrganizations** — Tests the simplest case where no de-duplication logic across child organizations is needed.
- **shouldReturnZeroForOrganizationWithNoMembers** *(edge case)* — Verifies the calculation is correct for an organization with zero members.
- **shouldReturnEmptyArrayWhenNoOrganizationsExist** *(edge case)* — Tests how the function behaves when the database query returns no results.
- **shouldRenderCorrectMemberCountFromAction** — This test ensures the UI component correctly consumes the new `memberCount` property from the server action's response, confirming the front-end change.
- **shouldDisplayEmptyStateWhenNoOrganizationsAreReturned** *(edge case)* — Verifies the component's behavior for the edge case where there is no data to display.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document for the Organization Management System. It is the most critical document for understanding the intended business logic, user roles, and rules governing main and sub-organizations, which is directly related to the member counting logic that ticket IDRE-647 aims to fix.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a high-level overview of the Organization Management feature set. It offers context on the existing functionality that is being modified and may contain information about how member counts were originally intended to be displayed.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be updated to reflect the new, accurate method for calculating the member count for a main organization (i.e., counting unique emails only once).
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: If this page details the features of organization management, it should be updated to describe the corrected member count logic.

## AI Confidence Scores
Plan: 80%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._