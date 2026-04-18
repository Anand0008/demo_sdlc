## IDRE-624: Party Portal: In the Cases page Filter by Organization functionality is not working as expected

**Jira Ticket:** [IDRE-624](https://orchidsoftware.atlassian.net//browse/IDRE-624)

## Summary
This plan addresses the bug where filtering cases by organization does not work. The fix involves updating the `getPartyCases` server action in `lib/party-actions.ts` to correctly apply the `organizationId` parameter to the database query, ensuring that only cases associated with the selected organization are returned.

## Implementation Plan

**Step 1: Apply organization filter in `getPartyCases` server action**  
In the `getPartyCases` function, locate the Prisma query responsible for fetching the list of cases. Modify the `where` clause of this query. When the `organizationId` parameter is present and not 'all', add a condition to ensure that the returned cases have at least one party associated with that `organizationId`. This will likely involve adding to an `AND` array in the `where` clause, with a condition like `{ parties: { some: { organizationId: organizationId } } }`.
Files: `lib/party-actions.ts`

**Risk Level:** LOW — The change is confined to a single server action and only affects the filtering logic for one field on the cases page. The front-end is already passing the correct parameter, so the fix is isolated to the backend data retrieval logic. There is a low risk of unintended side effects on other parts of the application.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
The `getPartyCases` server action was not utilizing the `organizationId` parameter in its database query. This change adds a new condition to the `where` clause of the Prisma query. When an `organizationId` is provided, the query will now correctly filter for cases that have at least one party associated with that specific organization, resolving the bug.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -677,6 +677,16 @@
       });
     }
 
+    if (organizationId) {
+      andConditions.push({
+        parties: {
+          some: {
+            organizationId: organizationId,
+          },
+        },
+      });
+    }
+
     if (andConditions.length > 0) {
       where.AND = andConditions;
     }
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldFilterCasesByOrganizationIdWhenProvided** — This test validates the primary bug fix. It ensures that when an organization ID is provided, the database query is correctly modified to filter cases belonging to that organization. This is a regression test to confirm the fix works as expected.
- **shouldReturnAllCasesWhenOrganizationIdIsNotProvided** — This test ensures that the function's existing behavior is unchanged when no organization filter is applied. It acts as a regression test to prevent unintended side effects.
- **shouldReturnEmptyArrayWhenNoCasesMatchOrganizationId** *(edge case)* — This test covers the edge case where a valid organization is selected, but it has no cases associated with it. The expected behavior is to return an empty list rather than an error.
- **shouldThrowErrorWhenDatabaseQueryFails** *(edge case)* — This test ensures that if the underlying database query fails for any reason (e.g., connection issue), the error is properly propagated up, allowing for graceful error handling in the UI.

## Confluence Documentation References

- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This page explicitly mentions that the "Organization Management Tool" is a recent development and that the team is working on "edge-case issues". This provides context that the feature is new, which aligns with the bug being reported in ticket IDRE-624.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — As the Product Requirements Document for the feature in question ("Organization Management System"), this page is the most critical source of information. It should contain the definitive business rules, user stories, and acceptance criteria that define how filtering cases by organization is intended to function. The developer must consult this to understand the expected behavior before fixing the bug.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a high-level overview of the "Organization Management" feature set, likely from a user's perspective. It is relevant for understanding the intended functionality and user experience of the feature that ticket IDRE-624 is addressing.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: The PRD might need to be updated to clarify the filtering logic if the current specification is ambiguous and contributed to the bug.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This user-facing document may need updates to clarify the corrected filter functionality.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._