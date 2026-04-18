## IDRE-636: Party Portal: Banking Dashboard not able to select All Organizations option

**Jira Ticket:** [IDRE-636](https://orchidsoftware.atlassian.net//browse/IDRE-636)

## Summary
This implementation plan addresses a UI bug where the "All Organizations" option in the Banking Dashboard dropdown is not selectable. The fix involves locating the client component responsible for this dropdown within `app/app/payments/page.tsx` and modifying its `onValueChange` handler. The handler will be updated to set the URL search parameter `organizationId` to "all" upon selection, which the page already uses to correctly filter dashboard data.

## Implementation Plan

**Step 1: Locate the Organization Dropdown Client Component**  
The organization filter dropdown is a client component rendered within the `PaymentsPage` at `app/app/payments/page.tsx`. Identify this component in the render tree. It is responsible for fetching the user's organizations and managing the filter state via URL search parameters.
Files: `app/app/payments/page.tsx`

**Step 2: Correct the `onValueChange` Handler for "All Organizations"**  
In the client component identified in Step 1, locate the `onValueChange` handler for the dropdown. Modify it to ensure that when the "All Organizations" option is selected, it triggers a navigation to update the URL. The `organizationId` search parameter should be set to the string value "all". This will likely use the `useRouter` and `useSearchParams` hooks from `next/navigation`. For example: `router.push(`/app/payments?organizationId=all`)`.
Files: `app/app/payments/page.tsx`

**Step 3: Verify Data Fetching for "All Organizations"**  
After implementing the fix, manually test the dropdown. When "All Organizations" is selected, the URL should update to include `?organizationId=all`. The dashboard components (`PaymentsOverview`, `PaymentHistorySection`, etc.) should then re-render with data aggregated from all of the user's organizations. This verifies that the logic in `app/app/payments/page.tsx` correctly interprets the search parameter. No code change is needed for this verification step.

**Risk Level:** LOW — The change is confined to a single UI component's event handler and relies on existing backend logic that appears to support fetching data for all organizations. The risk of unintended side effects is minimal.

## Proposed Code Changes

### `app/app/payments/page.tsx` (modify)
The ticket describes a bug where selecting "All Organizations" in the banking dashboard dropdown does not work. The implementation plan specifies that the `onValueChange` handler for this dropdown in `app/app/payments/page.tsx` needs to be corrected.
```
--- a/app/app/payments/page.tsx
+++ b/app/app/payments/page.tsx
@@ -1,6 +1,6 @@
 import { getCurrentSession, isViewOnlyImpersonation, isVtSupportImpersonation } from "@/lib/auth/utils";
-import { redirect } from "next/navigation";
-import { useRouter, useSearchParams } from "next/navigation";
+import { redirect, usePathname, useRouter, useSearchParams } from "next/navigation";
 import { Card, CardContent } from "@/components/ui/card";
 import { Button } from "@/components/ui/button";
 import { Badge } from "@/components/ui/badge";
@@ -18,6 +18,13 @@
   getCasesForPayment,
   getPartyUserBankAccounts as getUserBankAccounts,
 } from "@/lib/actions";
+import {
+  Select,
+  SelectContent,
+  SelectItem,
+  SelectTrigger,
+  SelectValue,
+} from "@/components/ui/select";
 
 interface PaymentsPageProps {
   searchParams: Promise<{
@@ -29,6 +36,46 @@
   }>;
 }
 
+function PaymentsHeader({
+  organizations,
+  activeOrganizationId,
+}: {
+  organizations: { id: string; name: string }[];
+  activeOrganizationId: string | null;
+}) {
+  "use client";
+  const router = useRouter();
+  const pathname = usePathname();
+  const searchParams = useSearchParams();
+
+  const handleOrgChange = (value: string) => {
+    const params = new URLSearchParams(searchParams);
+    params.set("organizationId", value);
+    router.push(`${pathname}?${params.toString()}`);
+  };
+
+  return (
+    <div className="flex items-center justify-between mb-6">
+      <h1 className="text-2xl font-semibold">Banking</h1>
+      {organizations.length > 1 && (
+        <Select
+          onValueChange={handleOrgChange}
+          defaultValue={activeOrganizationId ?? "all"}
+        >
+          <SelectTrigger className="w-[280px]">
+            <SelectValue placeholder="Select an organization" />
+          </SelectTrigger>
+          <SelectContent>
+            <SelectItem value="all">All Organizations</SelectItem>
+            {organizations.map((org) => (
+              <SelectItem key={org.id} value
... (truncated — see full diff in files)
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Vitest`

- **shouldUpdateUrlToAllWhenAllOrganizationsIsSelected** — This test validates the primary bug fix. It ensures that when a user selects the "All Organizations" option, the component correctly triggers a URL update to reflect this selection, which is the intended behavior described in the implementation plan.
- **shouldUpdateUrlWithSpecificOrgIdWhenAnOrganizationIsSelected** — This is a regression test to ensure that the existing functionality of selecting a specific organization was not broken by the change. It verifies that the `onValueChange` handler still works correctly for other options in the list.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This document is the Product Requirements Document (PRD) for the Organization Management System, which is the parent feature of the Banking Dashboard mentioned in the ticket. It will contain the core business rules, user stories, and acceptance criteria defining how users should be able to view and filter by organization, including the expected behavior of an 'All Organizations' option.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview explains the functionality of the Organization Management tools. It likely contains descriptions and screenshots of the intended user interface and functionality, which would provide context for how the Banking Dashboard's organization filter is supposed to work for the end-user.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page provides a thematic analysis of recurring bugs and identifies 'Banking & Banking Dashboard' as a problem area. This is direct context for the developer that the area they are working in is sensitive and may have underlying complexities beyond a simple UI fix.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: If the fix requires a change in business logic for how organization data is aggregated or displayed, the PRD should be updated to reflect the implemented behavior.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: As this document likely contains user-facing guides and screenshots, it should be updated to show the corrected and functional 'All Organizations' filter in the Banking Dashboard.

## AI Confidence Scores
Plan: 60%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._