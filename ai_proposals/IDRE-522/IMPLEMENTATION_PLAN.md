## IDRE-522: Role Adjustment: Admin-Support

**Jira Ticket:** [IDRE-522](https://orchidsoftware.atlassian.net//browse/IDRE-522)

## Summary
Adjust the `admin-support` role to restrict dashboard access to only cases and eligibility, and explicitly grant permissions for case creations, assignments, withdrawals, settlements, and notes.

## Implementation Plan

**Step 1: Update Admin-Support Resource Permissions**  
Update the `admin-support` role in the `roles` definition to only include permissions for `cases` and `eligibility` dashboards. Add specific permissions for case creations, assign to self, assign to others, withdrawals, settlements, and notes. Remove any other dashboard access (e.g., payments, banking, arbitration).
Files: `lib/auth/permissions.ts`

**Step 2: Update Admin-Support Route Permissions**  
Update the `routePermissions` configuration to ensure `admin-support` only has access to `/dashboard/cases` and `/dashboard/eligibility` routes. Remove access to other routes like `/dashboard/payments`, `/dashboard/arbitration`, etc.
Files: `lib/auth/route-permissions-config.ts`

**Step 3: Verify Eligibility Permissions Mapping**  
Ensure `getEligibilityPermissions` correctly maps the `admin-support` role to allow `canSelfAssign`, `canAssignToOthers`, `canMarkWithdrawal`, `canMarkSettlement`, and `canAddNotes`. If these are derived from `auth.api.userHasPermission`, ensure the permissions checked align with the updated `admin-support` role definition.
Files: `lib/utils/eligibility-permissions.ts`

**Risk Level:** LOW — The changes are isolated to role permission configurations and do not affect the underlying data models or core business logic.

## Proposed Code Changes

### `lib/auth/permissions.ts` (modify)
Restricts the `admin-support` role's resource permissions to only `cases` and `eligibility`. Adds the specific requested permissions for case management (create, assign, withdraw, settle, notes).
```typescript
--- a/lib/auth/permissions.ts
+++ b/lib/auth/permissions.ts
@@ -...@@
   "admin-support": {
-    cases: ["read", "update"],
-    eligibility: ["read", "update"],
-    payments: ["read", "update"],
-    arbitration: ["read", "update"],
-    banking: ["read", "update"],
-    company: ["read", "update"],
-    users: ["read", "update"],
-    reports: ["read", "update"],
+    cases: ["read", "create", "assign_self", "assign_others", "withdraw", "settle", "notes"],
+    eligibility: ["read", "update"],
   },
```

### `lib/auth/route-permissions-config.ts` (modify)
Removes `admin-support` from all route permissions except `/dashboard/cases` and `/dashboard/eligibility`, ensuring they cannot access unauthorized dashboards.
```typescript
--- a/lib/auth/route-permissions-config.ts
+++ b/lib/auth/route-permissions-config.ts
@@ -...@@
 export const routePermissions: Record<string, RoleName[]> = {
   "/dashboard/cases": ["master-admin", "admin-support", "vt-support", "accounting"],
   "/dashboard/eligibility": ["master-admin", "admin-support", "eligibility-specialist", "appeals-manager", "attorney"],
-  "/dashboard/payments": ["master-admin", "admin-support", "payment-admin", "payment-specialist"],
+  "/dashboard/payments": ["master-admin", "payment-admin", "payment-specialist"],
-  "/dashboard/arbitration": ["master-admin", "admin-support", "arbitrator", "arbitrator-contractor", "arbitrator-manager"],
+  "/dashboard/arbitration": ["master-admin", "arbitrator", "arbitrator-contractor", "arbitrator-manager"],
-  "/dashboard/banking": ["master-admin", "admin-support", "accounting"],
+  "/dashboard/banking": ["master-admin", "accounting"],
-  "/dashboard/company": ["master-admin", "admin-support"],
+  "/dashboard/company": ["master-admin"],
-  "/dashboard/users": ["master-admin", "admin-support"],
+  "/dashboard/users": ["master-admin"],
-  "/dashboard/reports": ["master-admin", "admin-support"],
+  "/dashboard/reports": ["master-admin"],
 };
```

### `lib/utils/eligibility-permissions.ts` (modify)
Updates the eligibility permissions mapping for `admin-support` to explicitly allow self-assignment, assigning to others, marking withdrawals, marking settlements, and adding notes, fulfilling the acceptance criteria.
```typescript
--- a/lib/utils/eligibility-permissions.ts
+++ b/lib/utils/eligibility-permissions.ts
@@ -...@@
     case "admin-support":
       return {
         canView: true,
         canEdit: true,
-        canSelfAssign: false,
-        canAssignToOthers: false,
-        canMarkWithdrawal: false,
-        canMarkSettlement: false,
-        canAddNotes: false,
+        canSelfAssign: true,
+        canAssignToOthers: true,
+        canMarkWithdrawal: true,
+        canMarkSettlement: true,
+        canAddNotes: true,
       };
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldAllowAdminSupportAccessToCasesAndEligibilityRoutes** — Verifies that the admin-support role has access to the cases and eligibility dashboards.
- **shouldDenyAdminSupportAccessToUnauthorizedDashboards** *(edge case)* — Ensures that the admin-support role is strictly restricted from accessing unauthorized dashboards (e.g., settings, users).
- **shouldGrantAdminSupportCorrectResourcePermissions** — Verifies that the admin-support role has the exact resource permissions requested in the ticket.
- **shouldMapAdminSupportToCorrectEligibilityActions** — Verifies that the eligibility-specific permission utilities correctly map the admin-support role to its allowed actions.

## AI Confidence Scores
Plan: 80%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._