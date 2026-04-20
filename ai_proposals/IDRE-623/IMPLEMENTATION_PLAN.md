## IDRE-623: Party Portal: Filter functionality not working as expected

**Jira Ticket:** [IDRE-623](https://orchidsoftware.atlassian.net//browse/IDRE-623)

## Summary
The current organization filter on the "Pay Online" page operates client-side, leading to incorrect case lists. The plan is to modify the filter's `onValueChange` handler in `app/app/payments/components/payment-form.tsx`. Instead of just updating local state, the new handler will use Next.js's `useRouter` to update the `organizationId` in the URL's query parameters. This will trigger a server-side data refetch via the page component (`app/app/payments/page.tsx`), which already uses this parameter to correctly filter cases via the `getCasesForPayment` action. This ensures the displayed cases accurately reflect the selected organization.

## Implementation Plan

**Step 1: Update Organization Filter to Trigger Server-Side Refetch**  
In the `PaymentForm` component, create a new handler function `handleOrganizationChange`. This function will take the selected organization ID as an argument. Inside this function, use the `useRouter` hook (already available as `router`) to update the URL's `organizationId` search parameter. If the selected value is "all", remove the `organizationId` parameter; otherwise, set it. This will trigger a server-side refetch of the cases, filtered by the selected organization. Then, update the `onValueChange` prop of the organization filter `Select` component (around line 1400) to use this new handler instead of `setOrganizationFilter`.
Files: `app/app/payments/components/payment-form.tsx`

**Risk Level:** LOW — The change is confined to a single client component and modifies UI behavior to align with existing server-side data fetching logic. The backend action already supports the required filtering, so no backend changes are needed. The risk of unintended side effects is low as the change is targeted at the filtering mechanism itself.

## Proposed Code Changes

### `app/app/payments/components/payment-form.tsx` (modify)
The previous implementation used `setOrganizationFilter` for the `onValueChange` handler, which only updated local state and performed client-side filtering on a potentially incomplete list of cases. This led to incorrect results.
```
--- a/app/app/payments/components/payment-form.tsx
+++ b/app/app/payments/components/payment-form.tsx
@@ -289,6 +289,16 @@
   const [showBankAccountRequiredDialog, setShowBankAccountRequiredDialog] =
     useState(false);
 
+  const handleOrganizationChange = (organizationId: string) => {
+    // Instead of client-side filtering, update the URL to trigger a server-side
+    // refetch of cases for the selected organization.
+    if (organizationId === "all") {
+      router.push('/app/payments');
+    } else {
+      router.push(`/app/payments?organizationId=${organizationId}`);
+    }
+  };
+
   const visibleCases = useMemo(() => {
     if (optimisticallyHiddenCaseIds.length === 0) {
       return cases;
@@ -1399,7 +1409,7 @@
                       {organizationFilterOptions.length > 0 && (
                         <Select
                           value={organizationFilter}
-                          onValueChange={setOrganizationFilter}
+                          onValueChange={handleOrganizationChange}
                         >
                           <SelectTrigger className="h-9 w-full text-sm sm:max-w-[220px] lg:max-w-[240px] xl:max-w-[260px]">
                             <SelectValue placeholder="Filter organizations" />
```

**New Dependencies:**
- `_No new dependencies needed._`

## Test Suggestions

Framework: `Vitest`

- **shouldUpdateUrlWhenOrganizationIsSelected** — Verifies that selecting an organization in the filter dropdown triggers a URL update with the correct organizationId query parameter.
- **shouldRemoveOrganizationIdFromUrlWhenFilterIsCleared** — Ensures that when the user clears the filter, the organizationId query parameter is removed from the URL, triggering a refetch for all cases.
- **shouldSetInitialFilterValueFromUrlParameter** — Verifies that the component correctly initializes its state from the URL query parameters on initial render, ensuring the filter reflects the current page state.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD is the most critical document. It defines the business rules and data model for the Organization Management system, which is at the core of the ticket. It details the two-level parent/sub-organization hierarchy and states that users can be associated with multiple organizations, which is essential context for debugging the filter logic.
- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This weekly summary provides important context by listing recently worked-on tickets related to the Organization Management tool. Specifically, it mentions IDRE-705 "Party Portal: Not able to see all organizations in filter dropdown", which is very similar to the bug in IDRE-623. This indicates that the feature is under active development and may have related complexities.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document provides high-level context about recurring bug themes. It explicitly calls out the "Party Portal & User Experience / Permissions" and "Organization & User Data Integrity" as fragile areas. This confirms that bugs related to what users can see based on their organization are a known category of issues, which is helpful for the developer to understand the problem's context.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: The document should be updated to explicitly define the expected filter behavior regarding the parent/sub-organization hierarchy. For example, it should clarify whether selecting a parent organization in a filter should also return results for all its sub-organizations.

## AI Confidence Scores
Plan: 100%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._