## IDRE-521: New Role: Case Manager

**Jira Ticket:** [IDRE-521](https://orchidsoftware.atlassian.net//browse/IDRE-521)

## Summary
Implement the 'Case Manager' role by configuring its granular permissions to act as a hybrid of admin support and eligibility, while strictly restricting access to Admin Actions, Admin Closures, and the ability to mark payments as paid.

## Implementation Plan

**Step 1: Configure Granular Permissions for Case Manager**  
Update the `roles` object to define granular permissions for the `case-manager` role. It should inherit or duplicate the combined permissions of `admin-support` and `eligibility-specialist`, but explicitly EXCLUDE `payment:update` (to prevent marking as paid), `admin_action:create`, `admin_action:update`, and `admin_closure:create`. Ensure it INCLUDES `case:create`, `case:assign`, `note:create`, `document:create`, `rfi:create`, `line_item:create`, `line_item:delete`, and `payment:read`.
Files: `lib/auth/permissions.ts`

**Step 2: Update Role Helper Functions**  
Review role helper functions such as `isPaymentRole` and `isAdminRole`. Ensure that `case-manager` is NOT included in `isPaymentRole` so that UI components relying on this helper do not allow the user to mark payments as paid. If `isAdminRole` is used to grant access to Admin Actions, ensure `case-manager` is excluded or that the UI is updated to use granular permission checks instead.
Files: `lib/auth/client-utils.ts`, `lib/auth/index.ts`

**Step 3: Enforce UI Restrictions for Case Manager**  
Audit the UI components for "Admin Actions", "Admin Closure", and "Mark as Paid". If these actions are protected by hardcoded role arrays (e.g., `['master-admin', 'admin-support']`), ensure `case-manager` is omitted. If they use `ShowIfPermission`, verify they check for the excluded permissions (`payment:update`, `admin_action:create`) rather than generic case update permissions. Ensure standard case closure methods remain accessible for the allowed statuses.
Files: `components/eligibility/case-actions.tsx`, `components/eligibility/eligibility-dashboard.tsx`

**Step 4: Verify Route Permissions**  
Verify the `routePermissions` configuration. The exploration report shows `case-manager` is already allowed on `/dashboard/cases`, `/dashboard/cases/create`, and `/dashboard/eligibility`. Ensure that `case-manager` is strictly EXCLUDED from `/dashboard/admin-closures` and any other admin-only routes.
Files: `lib/auth/route-permissions-config.ts`

**Risk Level:** LOW — The changes are isolated to role definitions, permission mappings, and UI visibility toggles. Since the role is new, it will not impact existing users in other roles. The primary risk is accidentally granting too much access, which is mitigated by explicitly excluding admin and payment update permissions.

**Deployment Notes:**
- Ensure that any active sessions for users assigned the `case-manager` role are refreshed or re-authenticated so the new granular permissions take effect.

## Proposed Code Changes

### `lib/auth/permissions.ts` (modify)
Defines the granular permissions for the new `case-manager` role. It includes permissions to create/assign cases, manage notes/documents/RFIs/line items, and read payments. It explicitly omits `payment:update`, `admin_action:create`, `admin_action:update`, and `admin_closure:create`.
```typescript
--- a/lib/auth/permissions.ts
+++ b/lib/auth/permissions.ts
@@ -80,6 +80,35 @@
     "report:read",
     "communication:read",
   ],
+  "case-manager": [
+    "case:read",
+    "case:create",
+    "case:update",
+    "case:assign",
+    "case:close",
+    "document:read",
+    "document:create",
+    "document:update",
+    "document:delete",
+    "note:read",
+    "note:create",
+    "note:update",
+    "note:delete",
+    "rfi:read",
+    "rfi:create",
+    "rfi:update",
+    "rfi:delete",
+    "line_item:read",
+    "line_item:create",
+    "line_item:update",
+    "line_item:delete",
+    "payment:read",
+    "party:read",
+    "party:create",
+    "party:update",
+    "user:read",
+    "report:read",
+    "communication:read",
+    "communication:create",
+  ],
   "eligibility-specialist": [
```

### `lib/auth/client-utils.ts` (modify)
Ensures that `case-manager` is strictly excluded from `isPaymentRole` and `isAdminRole` helpers, preventing accidental access to marking payments as paid or performing admin-level actions in the UI. *(Note: If `case-manager` was not previously added to these arrays, this diff serves as a safeguard).*
```typescript
--- a/lib/auth/client-utils.ts
+++ b/lib/auth/client-utils.ts
@@ -45,7 +45,7 @@
 export function isPaymentRole(role: string | null | undefined): boolean {
   if (!role) return false;
-  return ["payment-admin", "payment-specialist", "accounting", "master-admin", "case-manager"].includes(role);
+  return ["payment-admin", "payment-specialist", "accounting", "master-admin"].includes(role);
 }
 
 export function isAdminRole(role: string | null | undefined): boolean {
   if (!role) return false;
-  return ["master-admin", "admin-support", "capitol-bridge-admin", "case-manager"].includes(role);
+  return ["master-admin", "admin-support", "capitol-bridge-admin"].includes(role);
 }
```

### `components/eligibility/case-actions.tsx` (modify)
Updates the UI permission checks for Admin Actions and Admin Closures to use their specific granular permissions (`admin_action:create` and `admin_closure:create`) rather than the generic `case:update` permission. This ensures the Case Manager (who has `case:update` but lacks admin permissions) cannot see or use these actions.
```
--- a/components/eligibility/case-actions.tsx
+++ b/components/eligibility/case-actions.tsx
@@ -85,7 +85,7 @@
-  const canPerformAdminActions = hasPermission(userRole, "case:update");
+  const canPerformAdminActions = hasPermission(userRole, "admin_action:create");
 
-  const canAdminClose = hasPermission(userRole, "case:update");
+  const canAdminClose = hasPermission(userRole, "admin_closure:create");
```

### `components/eligibility/eligibility-dashboard.tsx` (modify)
Ensures the "Mark as Paid" action is strictly gated behind the `payment:update` permission, which the Case Manager role does not have, rather than a generic update permission.
```
--- a/components/eligibility/eligibility-dashboard.tsx
+++ b/components/eligibility/eligibility-dashboard.tsx
@@ -112,7 +112,7 @@
-  const canMarkAsPaid = hasPermission(userRole, "case:update");
+  const canMarkAsPaid = hasPermission(userRole, "payment:update");
```

### `lib/auth/route-permissions-config.ts` (modify)
Explicitly removes `case-manager` from the `/dashboard/admin-closures` route (if it was inadvertently added) to enforce the restriction against Admin Closures at the routing level.
```typescript
--- a/lib/auth/route-permissions-config.ts
+++ b/lib/auth/route-permissions-config.ts
@@ -145,7 +145,6 @@
   "/dashboard/admin-closures": {
     allowedRoles: [
       "master-admin",
       "admin-support",
-      "case-manager",
       "capitol-bridge-admin",
     ],
     description: "Admin closures management",
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest with React Testing Library`

- **should grant correct granular permissions and omit admin/payment permissions for case-manager** — Verifies that the case-manager role has the exact granular permissions required, acting as a hybrid role without admin/payment privileges.
- **should return false for isPaymentRole and isAdminRole when role is case-manager** *(edge case)* — Ensures the case-manager role is not accidentally treated as an admin or payment role by client utility helpers.
- **should hide Admin Actions and Admin Closure buttons for users lacking specific admin permissions** — Verifies that the UI correctly hides Admin Actions and Admin Closures based on granular permissions rather than the generic case:update permission.
- **should display payments but hide Mark as Paid button when user lacks payment:update permission** — Ensures that the 'Mark as Paid' action is strictly gated behind the payment:update permission.
- **should deny case-manager access to the admin-closures route** *(edge case)* — Verifies that route-level protection prevents the case-manager from accessing the Admin Closures page.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Describes the end-to-end case lifecycle and current actors (Internal Staff). The new Case Manager role will take over specific case creation and eligibility tasks outlined in this workflow.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — Outlines the main phases of a case (Eligibility, Payment Collection, Arbitration), which directly correspond to the dashboard and actions the new Case Manager role will interact with.

**Suggested Documentation Updates:**

- IDRE Worflow
- IDRE Case Workflow Documentation

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._