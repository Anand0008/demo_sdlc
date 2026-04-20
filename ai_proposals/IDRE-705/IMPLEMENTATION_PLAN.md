## IDRE-705: Party Portal: Not able to see All Organizations in the Filter By Organization dropdown

**Jira Ticket:** [IDRE-705](https://orchidsoftware.atlassian.net//browse/IDRE-705)

## Summary
This implementation plan addresses the missing "All Organizations" filter option by replacing the `<OrganizationSwitcher>` component in `app/app/cases/components/cases-page-client.tsx` with a standard `<Select>` dropdown. This new dropdown will be explicitly populated with an "All Organizations" option, ensuring it is always visible to the user, consistent with other parts of the application.

## Implementation Plan

**Step 1: Replace `OrganizationSwitcher` with a standard `Select` component**  
In the `CasesPageClient` component, replace the existing `<OrganizationSwitcher>` component with a standard `<Select>` component. This change provides direct control over the dropdown's options. The new `<Select>` component will be explicitly populated with a static "All Organizations" option, followed by the list of organizations passed in via props. The `onValueChange` handler will be adjusted to pass `null` to the `handleOrganizationChange` function when "All Organizations" is selected, which aligns with the existing logic for fetching data for all organizations.
Files: `app/app/cases/components/cases-page-client.tsx`

**Risk Level:** LOW — The change is isolated to a single client-side component and replaces an abstraction with a concrete, known-working pattern from elsewhere in the codebase. The backend already supports the "All Organizations" functionality, so no data-layer changes are needed. The risk is low as the change is straightforward and easily testable.

## Proposed Code Changes

### `app/app/cases/components/cases-page-client.tsx` (modify)
The `OrganizationSwitcher` component was not displaying the "All Organizations" option as required on the cases page. This change replaces it with a standard `Select` component from the UI library, which provides direct control over the dropdown's options. An "All Organizations" `SelectItem` is explicitly added to ensure it is always present. The `onValueChange` handler is configured to pass `null` to the existing `handleOrganizationChange` function when "All Organizations" is selected, which aligns with the backend logic for fetching data across all organizations.
```
--- a/app/app/cases/components/cases-page-client.tsx
+++ b/app/app/cases/components/cases-page-client.tsx
@@ -5,7 +5,14 @@
 import { getPartyCases } from "@/lib/actions";
 import { CasesTable } from "./cases-table";
 import { PaginationControls } from "@/components/shared/pagination-controls";
-import { OrganizationSwitcher } from "@/components/party/banking/organization-switcher";
+import {
+  Select,
+  SelectContent,
+  SelectItem,
+  SelectTrigger,
+  SelectValue,
+} from "@/components/ui/select";
 import { CaseStatusFilter } from "./case-status-filter";
 import { CasePartyTypeFilter } from "./case-party-type-filter";
 import { useDebounce } from "@/lib/hooks/use-debounce";
@@ -103,12 +110,28 @@
   return (
     <div className="space-y-6">
       <div className="flex items-center space-x-4">
-        <OrganizationSwitcher
-          organizations={organizations}
-          selectedOrganizationId={currentOrganizationId}
-          onSelect={handleOrganizationChange}
-          showAllOrganizations
-        />
+        <div className="flex flex-col gap-1">
+          <span className="text-xs font-medium uppercase text-muted-foreground">
+            Filter by Organization
+          </span>
+          <Select
+            value={currentOrganizationId ?? "all"}
+            onValueChange={(value) => {
+              handleOrganizationChange(value === "all" ? null : value);
+            }}
+          >
+            <SelectTrigger className="w-80 justify-between">
+              <SelectValue placeholder="Select an organization" />
+            </SelectTrigger>
+            <SelectContent>
+              <SelectItem value="all">All Organizations</SelectItem>
+              {organizations.map((org) => (
+                <SelectItem key={org.id} value={org.id}>
+                  {org.name}
+                </SelectItem>
+              ))}
+            </SelectContent>
+          </Select>
+        </div>
         <CaseStatusFilter
           currentStatus={currentStatu
... (truncated — see full diff in files)
```

**New Dependencies:**
- `No new dependencies needed.`

## Test Suggestions

Framework: `Vitest`

- **shouldRenderTheSelectDropdownWithAllOrganizationsAndGivenOrganizations** — Verifies that the new Select component correctly renders the default "All Organizations" option and dynamically populates the rest of the options from the organizations prop.
- **shouldCallHandleOrganizationChangeWithNullWhenAllOrganizationsIsSelected** — This test ensures that selecting "All Organizations" correctly triggers the event handler with a null value, which is the expected behavior for fetching data for all organizations.
- **shouldCallHandleOrganizationChangeWithTheCorrectIdWhenAnOrganizationIsSelected** — This test validates that selecting a specific organization triggers the event handler with the correct organization ID, preserving the existing filtering logic.
- **shouldRenderOnlyTheAllOrganizationsOptionWhenOrganizationsPropIsEmpty** *(edge case)* — This edge case test ensures the component behaves gracefully and remains functional even when there are no organizations to display, which could happen for new users or certain account types.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD is the primary source of truth for the Organization Management system. It defines the strict two-level parent/child data model, user-to-organization association rules, and technical implementation details for the organization hierarchy. This context is essential for a developer to correctly implement a filter that includes an 'All Organizations' view, as it dictates what data should be aggregated for a given user.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview describes the implemented features for Organization Management, including the master 'Organizations' tab and its filtering capabilities. It provides context on how organization data, including parent-sub relationships and types (Provider, Aggregator), is presented in the UI. This is relevant for ensuring the 'Filter by Organization' dropdown in the Party Portal is consistent with existing patterns.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: The 'Search & Selection UX' section could be updated to explicitly mention the 'All Organizations' filter option in the Party Portal to ensure requirements are fully captured.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This document should be updated to reflect the corrected functionality of the 'Filter By Organization' dropdown in the Party Portal once the fix for IDRE-705 is deployed.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._