## IDRE-565: Permission Adjustment, who can view Unpaid Disputes

**Jira Ticket:** [IDRE-565](https://orchidsoftware.atlassian.net//browse/IDRE-565)

## Summary
This plan grants the 'Capitol Bridge Admin' role access to the 'Unpaid Disputes' (Outstanding Payments) report. It involves updating the backend API route (`app/api/reports/outstanding-payments/route.ts`) to authorize the new role for data access and modifying the frontend component responsible for rendering the report selection cards on the `/dashboard/reports` page to make the card visible to users with that role.

## Implementation Plan

**Step 1: Update API Route Authorization for Outstanding Payments Report**  
In the GET request handler, locate the array of roles that are permitted to access the outstanding payments report data. Add the 'capitol-bridge-admin' role to this array. This will likely be a constant defined at the top of the file, used for an authorization check.
Files: `app/api/reports/outstanding-payments/route.ts`

**Step 2: Display 'Outstanding Payments Report' Card for Capitol Bridge Admin**  
The page `app/dashboard/reports/page.tsx` renders the report cards using the `ReportsDashboard` component. The developer needs to trace into the `ReportsDashboard` component from this file to find the conditional rendering logic for the 'Outstanding Payments Report' card. Once located, add the 'capitol-bridge-admin' role to the list of roles permitted to see the card. This approach mirrors the role check for `AuditingReports` visible in `app/dashboard/reports/page.tsx`.
Files: `app/dashboard/reports/page.tsx`

**Risk Level:** LOW — The changes are confined to permission checks for a single, non-critical report. The primary risk is the exact location of the UI logic for rendering the report card is in a component (`ReportsDashboard`) whose source was not provided, but it is directly referenced from an identified file, making it traceable. The backend change is a simple addition to an authorization list.

## Proposed Code Changes

### `app/api/reports/outstanding-payments/route.ts` (modify)
This change adds the 'capitol-bridge-admin' role to the list of roles authorized to access the outstanding payments report data from the API, fulfilling the backend permission requirement.
```typescript
--- a/app/api/reports/outstanding-payments/route.ts
+++ b/app/api/reports/outstanding-payments/route.ts
@@ -93,6 +93,7 @@
   "master-admin",
   "payment-admin",
   "payment-specialist",
+  "capitol-bridge-admin",
 ];
 
 export async function GET(req: NextRequest) {
```

### `app/dashboard/reports/page.tsx` (modify)
This change adds the 'capitol-bridge-admin' role to the `AUDITING_REPORT_ROLES` constant. This makes the `AuditingReports` component, which is assumed to contain the 'Outstanding Payments' report card, visible to users with this role, matching the backend API permissions.
```
--- a/app/dashboard/reports/page.tsx
+++ b/app/dashboard/reports/page.tsx
@@ -6,7 +6,8 @@
 const AUDITING_REPORT_ROLES: ReadonlyArray<ReportAccessRole> = [
   "master-admin",
   "payment-admin",
-  "payment-specialist"
+  "payment-specialist",
+  "capitol-bridge-admin"
 ];
 
 export default async function ReportsPage() {
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldReturn200OkForUserWithCapitolBridgeAdminRole** — Verifies that a user with the newly added 'capitol-bridge-admin' role can successfully access the outstanding payments API endpoint.
- **shouldReturn403ForbiddenForUserWithUnauthorizedRole** *(edge case)* — Verifies that a user with an unauthorized role is properly denied access to the API endpoint.
- **shouldRenderTheOutstandingPaymentsCardForCapitolBridgeAdminUser** — Ensures the "Outstanding Payments" report card is visible on the dashboard for a user with the 'capitol-bridge-admin' role.
- **shouldNotRenderTheOutstandingPaymentsCardForUnauthorizedUser** *(edge case)* — Ensures the "Outstanding Payments" report card is hidden for users who do not have the required role.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page details the end-to-end case and payment lifecycle for disputes. Understanding this process is essential context for a developer working on a report about 'Unpaid Disputes', as it clarifies the business steps that lead to the data shown in the report.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page provides critical operational context, identifying the 'Payments & Refunds Logic / Workflow' as a 'major complexity hotspot' prone to high-impact production issues. This is a direct warning to the developer to exercise caution and ensure thorough testing when modifying access to a report on payment data.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This document provides a high-level overview of the case workflow, explicitly mentioning the 'Payment Collection' phase. This is directly relevant as the 'Unpaid Disputes' report is a view into this specific stage of the business process.

**Suggested Documentation Updates:**

- IDRE Worflow
- IDRE Case Workflow Documentation

## AI Confidence Scores
Plan: 80%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._