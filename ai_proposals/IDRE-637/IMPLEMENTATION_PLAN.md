## IDRE-637: Party Portal: Members page not able to see All Organizations option in the dropdown

**Jira Ticket:** [IDRE-637](https://orchidsoftware.atlassian.net//browse/IDRE-637)

## Summary
This plan addresses the missing "All Organizations" option by modifying the `app/app/payments/page.tsx` server component. It will conditionally prepend an "All Organizations" entry to the list of organizations passed to the UI's filter dropdown. This is a targeted, single-file change that leverages existing backend logic for handling the "all" organization view.

## Implementation Plan

**Step 1: Identify organization data fetching in PaymentsPage**  
In the `PaymentsPage` server component, locate the server action call that fetches the list of organizations for the current user. After the organization data is retrieved, insert logic to check if the user is a member of more than one organization.
Files: `app/app/payments/page.tsx`

**Step 2: Conditionally add "All Organizations" to the list**  
If the user belongs to more than one organization, prepend a static object to the beginning of the organizations array. This object should represent the "All Organizations" option, for example: `{ id: "all", name: "All Organizations" }`. This modified array will then be passed down to the client component that renders the dropdown.
Files: `app/app/payments/page.tsx`

**Step 3: Pass modified organization list to the filter component**  
Ensure the modified organizations array is correctly passed as a prop to the client component responsible for rendering the filter dropdown. No changes are expected for the downstream components, as the page already contains logic to handle `organizationId === "all"` in the search parameters, which was confirmed in the exploration report.
Files: `app/app/payments/page.tsx`

**Risk Level:** LOW — The change is additive and contained within a single server component. The backend logic to handle the "all" organization scope already exists, as seen in the exploration report for `app/app/payments/page.tsx`. The risk of unintended side effects is minimal.

## Proposed Code Changes

### `app/app/payments/page.tsx` (modify)
As per the implementation plan, this change introduces logic to prepend an "All Organizations" option to the list of organizations passed to the `PaymentHistorySection`. This is done conditionally, only when a user belongs to more than one organization. The `organizationsForFilter` variable is created to hold this potentially modified list, which is then passed down as a prop, enabling the desired functionality in the UI without altering downstream components.
```
--- a/app/app/payments/page.tsx
+++ b/app/app/payments/page.tsx
@@ -75,12 +75,21 @@
     getUserBankAccounts(),
   ]);
 
+  const userOrganizations = session.user.organizations ?? [];
+  let organizationsForFilter = userOrganizations;
+  if (userOrganizations.length > 1) {
+    organizationsForFilter = [
+      { id: "all", name: "All Organizations" },
+      ...userOrganizations,
+    ];
+  }
+
   return (
     <div className="flex flex-col gap-6">
       <StripeSuccessHandler />
       {viewOnly && (
         <Alert variant="info">
           <AlertTriangle className="h-4 w-4" />
           <AlertTitle>View-Only Mode</AlertTitle>
@@ -121,7 +130,7 @@
       <Suspense fallback={<PaymentHistorySkeleton />}>
         <PaymentHistorySection
           initialCases={initialCases}
-          organizations={session.user.organizations ?? []}
+          organizations={organizationsForFilter}
           activeOrganizationId={activeOrganizationId}
           partyType={searchParamsResolved.partyType ?? null}
         />
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldPrependAllOrganizationsOptionWhenUserHasMultipleOrganizations** — Verifies that when a user belongs to more than one organization, the "All Organizations" option is correctly added to the start of the list passed to the child component. This is the primary success scenario.
- **shouldNotPrependAllOrganizationsOptionWhenUserHasOneOrganization** *(edge case)* — Tests the boundary condition where a user has only one organization. In this case, the "All Organizations" filter is redundant and should not be displayed.
- **shouldPassEmptyArrayWhenUserHasNoOrganizations** *(edge case)* — Tests the edge case where a user is not part of any organization. The component should handle this gracefully and pass an empty array down.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the Organization Management System, which is the feature area for this ticket. This document should contain the definitive business rules and acceptance criteria for how the organization dropdown and member visibility are supposed to function.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a user-facing or internal overview of the Organization Management feature set. It likely contains descriptions and screenshots of the intended functionality, which will provide context for how the UI should behave.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be reviewed to ensure the requirement for the "All Organizations" option is clearly defined. If the original requirement was ambiguous, it should be updated to prevent future misinterpretations.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: If this page includes screenshots or detailed descriptions of the Members page UI, they may need to be updated to reflect the corrected dropdown functionality after the fix is implemented.

## AI Confidence Scores
Plan: 80%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._