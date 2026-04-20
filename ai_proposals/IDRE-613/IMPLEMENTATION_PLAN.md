## IDRE-613: Not able to reassign sub-organization to main organization

**Jira Ticket:** [IDRE-613](https://orchidsoftware.atlassian.net//browse/IDRE-613)

## Summary
This plan resolves the bug that prevents reassigning a sub-organization to a main organization. The root cause is improper permission checking that does not account for organization hierarchies. The fix involves updating the `getCaseDetails` server action in `lib/actions/party-case-details.ts` to include sub-organizations when determining a user's access to cases. This will allow the permission checks to pass, unblocking the reassignment operation.

## Implementation Plan

**Step 1: Modify `getCaseDetails` to recognize sub-organization relationships**  
Update the `getCaseDetails` function to correctly determine a user's organizational access by including sub-organizations. This will fix permission checks that currently fail when trying to manage sub-organizations. First, after fetching the user's direct organization IDs into the `orgIds` constant, add a Prisma query to fetch the IDs of all sub-organizations belonging to those direct organizations. Then, combine the direct and sub-organization IDs into a new `allOrgIds` array, ensuring uniqueness. Finally, in the `whereClause` for the `prisma.case.findFirst` call, replace `orgIds` with `allOrgIds` to ensure cases related to sub-organizations are included in the access check.
Files: `lib/actions/party-case-details.ts`

**Risk Level:** LOW — The change is confined to a single server action and expands data visibility in a logical way that reflects the intended organizational hierarchy. This is a low-risk bug fix that is unlikely to cause negative side effects.

## Proposed Code Changes

### `lib/actions/party-case-details.ts` (modify)
As per the implementation plan, the `getCaseDetails` function was only checking for cases associated with the user's direct organizations. This change extends the logic to also fetch and include all sub-organizations of the user's organizations. By using the combined list of direct and sub-organization IDs (`allOrgIds`) in the case query, we ensure that permission checks correctly account for the organizational hierarchy, resolving the bug that blocked the reassignment of sub-organizations.
```typescript
--- a/lib/actions/party-case-details.ts
+++ b/lib/actions/party-case-details.ts
@@ -30,18 +30,29 @@
     });
 
     const orgIds = memberships.map((m) => m.organizationId);
+
+    // Also find all sub-organizations of the user's organizations
+    const subOrgs = await prisma.organization.findMany({
+      where: {
+        parentId: { in: orgIds },
+      },
+      select: { id: true },
+    });
+    const subOrgIds = subOrgs.map((org) => org.id);
+
+    const allOrgIds = [...new Set([...orgIds, ...subOrgIds])];
 
     // Check both organization-based AND user-based access
     // This handles cases where users are directly associated or through organizations
     const whereClause = {
       id: caseId,
       OR: [
         // Direct user association (for backwards compatibility or cases without proper org assignment)
         { initiatingParty: { userId } },
         { nonInitiatingParty: { userId } },
         // Organization-based access (primary method)
-        ...(orgIds.length > 0
+        ...(allOrgIds.length > 0
           ? [
-              { initiatingPartyOrganizationId: { in: orgIds } },
-              { nonInitiatingPartyOrganizationId: { in: orgIds } },
+              { initiatingPartyOrganizationId: { in: allOrgIds } },
+              { nonInitiatingPartyOrganizationId: { in: allOrgIds } },
             ]
           : []),
       ],
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldReturnCaseDetailsWhenUserBelongsToParentOrganization** — This is the primary regression test. It simulates the exact scenario reported in the bug: a user belonging to a parent organization should be able to access resources (cases) owned by a sub-organization. This verifies that the fix correctly includes sub-organization IDs in the permission check.
- **shouldReturnCaseDetailsWhenUserBelongsToDirectOrganization** — This test verifies that the change does not introduce a regression for the standard "happy path" scenario. Users must still be able to access cases that belong to their direct organization.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This document is the Product Requirements Document (PRD) for the feature area in question. It should contain the definitive business rules, constraints, and expected behavior for managing organizations and sub-organizations, which is essential for resolving the bug.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This page provides an overview of the Organization Management feature as part of a release. It can offer context on the intended functionality and user-facing aspects, which helps in understanding the scope of the bug.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be reviewed and updated to clarify the specific business rules and validation logic for reassigning a sub-organization. If the rules are ambiguous, this ticket provides an opportunity to refine them.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: If this page contains user-facing guides on the feature, it will need to be updated to reflect the corrected workflow for reassigning organizations once the bug is fixed.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._