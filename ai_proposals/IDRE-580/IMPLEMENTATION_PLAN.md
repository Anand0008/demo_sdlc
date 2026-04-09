## IDRE-580: New Role: VT Support

**Jira Ticket:** [IDRE-580](https://orchidsoftware.atlassian.net//browse/IDRE-580)

## Summary
Implement the 'VT Support' role by wiring up its granular permissions, route access, and report access using the existing constants and role definitions.

## Implementation Plan

**Step 1: Define granular permissions for VT Support**  
Add `vt-support` to the `roles` object with the appropriate statements based on the ticket requirements. Use the constants from `lib/constants/vt-support.ts` if applicable, or manually map the permissions (e.g., view cases, view payments, full invoice management, no banking access). Update `roleHierarchy` if necessary.
Files: `lib/auth/permissions.ts`

**Step 2: Configure route access for VT Support**  
Update the `routePermissions` configuration to include `vt-support` in the allowed roles for the appropriate routes (e.g., `/dashboard/company`, `/dashboard/organizations`, `/dashboard/cases`, `/dashboard/reports`, etc.) and ensure it is excluded from restricted routes (e.g., `/dashboard/banking`, `/dashboard/cms-invoices`).
Files: `lib/auth/route-permissions-config.ts`

**Step 3: Update server-side permission helpers**  
Update server-side permission helper functions (e.g., `canAccessCases`, `canAccessReports`, `canAccessCompany`) to include the `vt-support` role where appropriate, ensuring view-only or full access aligns with the ticket requirements.
Files: `lib/auth/utils.ts`

**Step 4: Update report access roles**  
Add `vt-support` to the relevant report access constants (e.g., `REPORT_ACCESS_ROLES`, `OUTSTANDING_PAYMENTS_REPORT_ROLES`) to grant access to the specific reports mentioned in the ticket (Unpaid Disputes, Outstanding Payments, Due Dates, Case Management Analytics, Team Performance Analytics).
Files: `lib/constants/roles.ts`

**Risk Level:** LOW — The changes are isolated to RBAC configuration files and do not alter existing logic for other roles. The constants for VT Support are already defined, reducing the risk of misinterpretation.

## Proposed Code Changes

### `lib/auth/permissions.ts` (modify)
Define granular permissions for the `vt-support` role based on the ticket requirements, granting access to specific company actions, organization management, view-only sections, and specific reports.
```typescript
--- a/lib/auth/permissions.ts
+++ b/lib/auth/permissions.ts
@@ -50,6 +50,33 @@
   // ... existing roles ...
+  "vt-support": [
+    "company:read",
+    "company:impersonate",
+    "company:manage-users",
+    "company:manage-org-members",
+    "company:invoice-management",
+    "company:attach-user",
+    "company:delete-invoices",
+    "company:copy-banking",
+    "company:pay-disputes-invoice",
+    "organizations:read",
+    "organizations:edit",
+    "organizations:invite-user",
+    "organizations:manage-members",
+    "organizations:financial-controls:partial",
+    "organizations:combine",
+    "cases:read",
+    "eligibility:read",
+    "arbitration:read",
+    "admin-closures:read",
+    "payments:read",
+    "reports:read",
+    "reports:unpaid-disputes",
+    "reports:outstanding-payments",
+    "reports:due-dates",
+    "reports:case-management-analytics",
+    "reports:team-performance-analytics"
+  ],
```

### `lib/auth/route-permissions-config.ts` (modify)
Grant the `vt-support` role access to the allowed routes (Company, Organizations, Cases, Eligibility, Arbitration, Admin Closures, Payments, Reports) while ensuring it is excluded from restricted routes (Banking, CMS Invoices).
```typescript
--- a/lib/auth/route-permissions-config.ts
+++ b/lib/auth/route-permissions-config.ts
@@ -10,15 +10,15 @@
 export const routePermissions = {
   // ... existing routes ...
-  "/dashboard/company": ["master-admin", /* other roles */],
+  "/dashboard/company": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/organizations": ["master-admin", /* other roles */],
+  "/dashboard/organizations": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/cases": ["master-admin", /* other roles */],
+  "/dashboard/cases": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/eligibility": ["master-admin", /* other roles */],
+  "/dashboard/eligibility": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/arbitration": ["master-admin", /* other roles */],
+  "/dashboard/arbitration": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/admin-closures": ["master-admin", /* other roles */],
+  "/dashboard/admin-closures": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/payments": ["master-admin", /* other roles */],
+  "/dashboard/payments": ["master-admin", "vt-support", /* other roles */],
-  "/dashboard/reports": ["master-admin", /* other roles */],
+  "/dashboard/reports": ["master-admin", "vt-support", /* other roles */],
   // Ensure /dashboard/banking and /dashboard/cms-invoices DO NOT include "vt-support"
```

### `lib/auth/utils.ts` (modify)
Update server-side permission helper functions to include the `vt-support` role where appropriate, aligning with the route permissions.
```typescript
--- a/lib/auth/utils.ts
+++ b/lib/auth/utils.ts
@@ -20,10 +20,10 @@
 // Example updates to server-side permission helpers
 export function canAccessCases(role: string) {
-  return ["master-admin", "case-manager"].includes(role);
+  return ["master-admin", "case-manager", "vt-support"].includes(role);
 }
 
 export function canAccessReports(role: string) {
-  return ["master-admin"].includes(role);
+  return ["master-admin", "vt-support"].includes(role);
 }
 
 export function canAccessCompany(role: string) {
-  return ["master-admin"].includes(role);
+  return ["master-admin", "vt-support"].includes(role);
 }
```

### `lib/constants/roles.ts` (modify)
Add `vt-support` to the relevant report access constants to grant access to the specific reports mentioned in the ticket (Unpaid Disputes, Outstanding Payments, Due Dates, Case Management Analytics, Team Performance Analytics).
```typescript
--- a/lib/constants/roles.ts
+++ b/lib/constants/roles.ts
@@ -15,26 +15,32 @@
 export const REPORT_ACCESS_ROLES = [
   "master-admin",
+  "vt-support",
   // ... other roles
 ];
 
 export const OUTSTANDING_PAYMENTS_REPORT_ROLES = [
   "master-admin",
+  "vt-support",
   // ... other roles
 ];
 
 export const UNPAID_DISPUTES_REPORT_ROLES = [
   "master-admin",
+  "vt-support",
   // ... other roles
 ];
 
 export const DUE_DATES_REPORT_ROLES = [
   "master-admin",
+  "vt-support",
   // ... other roles
 ];
 
 export const CASE_MANAGEMENT_ANALYTICS_ROLES = [
   "master-admin",
+  "vt-support",
   // ... other roles
 ];
 
 export const TEAM_PERFORMANCE_ANALYTICS_ROLES = [
   "master-admin",
+  "vt-support",
   // ... other roles
 ];
```

## Test Suggestions

Framework: `Jest/Vitest`

- **should grant correct allowed permissions for vt-support role** — Verifies that the VT Support role has the correct allowed granular permissions as per the ticket requirements.
- **should deny restricted permissions for vt-support role** *(edge case)* — Verifies that the VT Support role is explicitly denied access to restricted actions.
- **should allow vt-support to access permitted routes** — Verifies that the VT Support role can access its permitted dashboard routes.
- **should deny vt-support access to restricted routes** *(edge case)* — Verifies that the VT Support role cannot access restricted dashboard routes.
- **should grant vt-support access to specific reports** — Verifies that the VT Support role has access to the specific reports outlined in the ticket.
- **should return correct boolean from server-side permission helpers for vt-support** — Verifies that the server-side utility functions correctly evaluate permissions for the VT Support role.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._