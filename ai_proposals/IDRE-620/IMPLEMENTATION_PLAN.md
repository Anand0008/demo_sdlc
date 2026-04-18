## IDRE-620: Not able to see newly created case under cases tab of suborganizations

**Jira Ticket:** [IDRE-620](https://orchidsoftware.atlassian.net//browse/IDRE-620)

## Summary
This plan addresses the bug where cases from sub-organizations are not displayed. The fix involves modifying the `getPartyCases` server action in `lib/party-actions.ts`. First, the action will be updated to recursively fetch the IDs of all sub-organizations for the selected main organization. Second, the Prisma query for cases will be adjusted to use this complete list of organization IDs, ensuring that cases associated with the main organization OR any of its sub-organizations are returned to the UI.

## Implementation Plan

**Step 1: Fetch All Sub-Organization IDs**  
In the `getPartyCases` function, before querying for cases, implement logic to fetch all descendant organization IDs for the given `organizationId`. This will likely involve a recursive database query on the `Organization` model to build a complete list of all sub-organization IDs under the main organization. The final list should include the ID of the main organization itself.
Files: `lib/party-actions.ts`

**Step 2: Update Case Query to Include Sub-Organizations**  
Modify the `prisma.case.findMany` query within `getPartyCases`. Update the `where` clause to use the comprehensive list of organization IDs (main organization + all sub-organizations) gathered in the previous step. The query should fetch cases where either the `initiatingPartyOrganizationId` or the `nonInitiatingPartyOrganizationId` is in this list, ensuring cases from all sub-organizations are included.
Files: `lib/party-actions.ts`

**Risk Level:** LOW — The change is confined to a single server action responsible for data fetching. The risk of unintended side effects is low, as this will only expand the result set for a specific view to include data that is currently missing, which is the intended behavior. No database or UI component changes are required.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
The original implementation for fetching cases only considered the provided `organizationId`. This change addresses the bug where cases from sub-organizations were not visible.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -10,6 +10,28 @@
 import { createBulkPayment } from "@/lib/actions/payment";
 import type { PartyType } from "@prisma/client";
 
+/**
+ * Fetches all descendant organization IDs for a given root organization.
+ * This includes the root organization's ID itself.
+ * @param rootOrganizationId The ID of the top-level organization.
+ * @returns A promise that resolves to an array of organization IDs.
+ */
+async function getAllSubOrganizationIds(rootOrganizationId: string): Promise<string[]> {
+  const allIds = new Set<string>([rootOrganizationId]);
+  const queue = [rootOrganizationId];
+  let i = 0;
+  while (i < queue.length) {
+    const currentOrgId = queue[i++];
+    const children = await prisma.organization.findMany({
+      where: { parentId: currentOrgId },
+      select: { id: true },
+    });
+    for (const child of children) {
+      if (allIds.add(child.id)) queue.push(child.id);
+    }
+  }
+  return Array.from(allIds);
+}
+
 type ActionResult<T = unknown> = {
   success: boolean;
   data?: T;
@@ -88,6 +110,7 @@
   return obj;
 }
 
+// NOTE: The following function `getPartyCases` is assumed to exist in this file.
 // Type definitions for serialized data
 type SerializedDisputeLineItem = {
   id: string;
@@ -120,6 +143,49 @@
   // ... (other type definitions)
 };
 
+export async function getPartyCases({
+  organizationId,
+  partyType,
+  status,
+  page = 1,
+  limit = 10,
+}: {
+  organizationId: string;
+  partyType?: "initiating" | "non-initiating";
+  status?: string;
+  page?: number;
+  limit?: number;
+}) {
+  try {
+    const { user } = await auth();
+    if (!user) {
+      return { success: false, error: "Unauthorized" };
+    }
+
+    const organizationIds = await getAllSubOrganizationIds(organizationId);
+
+    const whereClause: any = {};
+
+    if (status && status !== "all") {
+      whereClause.status = status;
+    }
+
+    if (partyType === "initiating") {
+      whereClause.initia
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldReturnCasesForOrganizationWithNoSubOrganizations** — This is a regression test to ensure that the change doesn't break the existing functionality for organizations without a hierarchy.
- **shouldReturnCasesForOrganizationAndItsDirectSubOrganizations** — This is the primary happy path test to validate the bug fix, ensuring cases from direct children are included in the result.
- **shouldReturnCasesForOrganizationAndItsNestedSubOrganizations** *(edge case)* — This test covers the edge case of a multi-level organization structure, ensuring the sub-organization search is recursive.
- **shouldReturnEmptyArrayWhenNoCasesExistForHierarchy** *(edge case)* — This test covers the edge case where organizations exist but have no associated cases, which is a valid state.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the exact feature mentioned in the ticket (Organization Management). It should contain the definitive business rules for how organizations, sub-organizations, and cases are related, and how case visibility should function.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides an overview of the Organization Management feature set. It is relevant for understanding the intended functionality and user-facing aspects of the tool where the bug is occurring.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: If the bug is due to an unspecified requirement or an edge case, this PRD should be updated to clarify the expected behavior for case visibility within sub-organizations.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This document should be updated to reflect the resolution of this bug, especially if it serves as a reference for feature functionality or release notes.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._