## IDRE-521: New Role: Case Manager

**Jira Ticket:** [IDRE-521](https://orchidsoftware.atlassian.net//browse/IDRE-521)

## Summary
Implement the 'Case Manager' role by defining its granular permissions in the RBAC matrix, updating default routing, and ensuring UI components correctly enforce its hybrid access (allowing case/eligibility management while restricting admin closures and payment modifications).

## Implementation Plan

**Step 1: Route Case Manager to Default Dashboard**  
Update the `getDefaultDashboardForRole` function to include a switch case for `"case-manager"`, returning `"/dashboard/cases"` (or `"/dashboard/eligibility"`) so users with this role are routed correctly upon login.
Files: `lib/auth/middleware-utils.ts`

**Step 2: Define Granular Permissions in RoleStatements**  
Locate the `RoleStatements` permission matrix. Add a new entry for `"case-manager"`. Grant `create`, `read`, `update`, and `assign` actions for the `cases` resource. Grant `read` and `update` for `eligibility`. Grant `create`, `read`, `update`, `delete` for `notes`, `line_items`, and `documents`. Crucially, grant ONLY `read` for `payments` (do NOT grant `update` or `mark_paid`), and explicitly omit any permissions for `admin_actions` and `admin_closures`.
Files: `lib/auth/utils.ts`

**Step 3: Update Role Hierarchy and Manageable Roles**  
Update `roleHierarchy` to include `"case-manager"` with an appropriate numeric weight (e.g., between `admin-support` and `eligibility-specialist`). Update `getManageableRoles` to ensure the Case Manager can view and assign cases to themselves and other relevant internal staff.
Files: `lib/auth/permissions.ts`

**Step 4: Configure Client Role Helpers**  
Review role helper functions such as `isAdminRole` and `isPaymentRole`. Ensure `"case-manager"` is explicitly EXCLUDED from these to prevent accidental access to Admin Actions, Admin Closures, and payment modification UI. If there are helpers like `isEligibilityRole`, ensure `"case-manager"` is INCLUDED.
Files: `lib/auth/client-utils.ts`, `lib/auth/index.ts`

**Step 5: Verify UI Component Permission Checks**  
Review the rendering logic for case actions (Mark as Paid, Admin Closure, Admin Actions, RFI, Notes, Line Items). Ensure they rely on the `userPermissions` object passed as props (which will now correctly reflect the `RoleStatements`). If any hardcoded role arrays exist (e.g., `['admin-support', 'eligibility-specialist']`), add `"case-manager"` to the allowed actions (RFI, notes, documents) and ensure it is absent from restricted actions (Admin Closure, Mark as Paid).
Files: `components/eligibility/case-actions.tsx`, `components/eligibility/eligibility-dashboard.tsx`

**Risk Level:** LOW — The changes are strictly additive to the RBAC system and isolated to permission definitions and routing. Since the 'case-manager' role is new, it will not affect the permissions or workflows of existing roles.

**Deployment Notes:**
- Ensure that any active sessions for users newly assigned to the 'case-manager' role are refreshed so they pick up the new RoleStatements and route permissions.

## Proposed Code Changes

### `lib/auth/middleware-utils.ts` (modify)
Routes the new Case Manager role to the default cases dashboard upon login, matching the behavior of Admin Support.
```typescript
@@ -... @@
 export function getDefaultDashboardForRole(role: RoleName): string {
   switch (role) {
     case "master-admin":
     case "admin-support":
+    case "case-manager":
       return "/dashboard/cases";
     case "eligibility-specialist":
       return "/dashboard/eligibility";
```

### `lib/auth/utils.ts` (modify)
Defines the granular permissions for the Case Manager role. They have full CRUD on notes, line items, and documents, can create/assign cases, but only have read access to payments (cannot mark as paid) and no access to admin actions/closures.
```typescript
@@ -... @@
 export const RoleStatements: Record<RoleName, Partial<Record<Resource, Action[]>>> = {
   "master-admin": {
     // ...
   },
+  "case-manager": {
+    cases: ["create", "read", "update", "assign"],
+    eligibility: ["read", "update"],
+    notes: ["create", "read", "update", "delete"],
+    line_items: ["create", "read", "update", "delete"],
+    documents: ["create", "read", "update", "delete"],
+    payments: ["read"],
+  },
   "eligibility-specialist": {
```

### `lib/auth/permissions.ts` (modify)
Inserts the Case Manager into the role hierarchy between Admin Support and Eligibility Specialist. Updates manageable roles so they can assign cases to themselves and other relevant internal staff.
```typescript
@@ -... @@
 export const roleHierarchy: Record<RoleName, number> = {
   "master-admin": 100,
   "admin-support": 90,
+  "case-manager": 85,
   "eligibility-specialist": 80,
   // ...
 }
 
@@ -... @@
 export function getManageableRoles(role: RoleName): RoleName[] {
   switch (role) {
     case "master-admin":
       // ...
     case "admin-support":
-      return ["eligibility-specialist", "view-only"];
+      return ["case-manager", "eligibility-specialist", "view-only"];
+    case "case-manager":
+      return ["case-manager", "eligibility-specialist", "view-only"];
     // ...
   }
 }
```

### `lib/auth/client-utils.ts` (modify)
Updates client-side role helpers to include the Case Manager in eligibility-related checks, while explicitly keeping them out of admin-only checks.
```typescript
@@ -... @@
 export function isEligibilityRole(role: string | null | undefined): boolean {
   if (!role) return false;
-  return ["master-admin", "admin-support", "eligibility-specialist"].includes(role);
+  return ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(role);
 }
 
 export function isAdminRole(role: string | null | undefined): boolean {
   if (!role) return false;
   // Ensure case-manager is NOT added here
   return ["master-admin", "admin-support"].includes(role);
 }
```

### `components/eligibility/case-actions.tsx` (modify)
Grants the Case Manager access to RFI, Line Items, and Document management in the UI. (Note: Admin Closure and Mark as Paid checks remain unchanged, naturally excluding the Case Manager).
```
@@ -... @@
-  const canRFI = ["master-admin", "admin-support", "eligibility-specialist"].includes(userRole);
+  const canRFI = ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(userRole);
 
-  const canEditLineItems = ["master-admin", "admin-support", "eligibility-specialist"].includes(userRole);
+  const canEditLineItems = ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(userRole);
 
-  const canManageDocuments = ["master-admin", "admin-support", "eligibility-specialist"].includes(userRole);
+  const canManageDocuments = ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(userRole);
```

### `components/eligibility/eligibility-dashboard.tsx` (modify)
Ensures the Case Manager can view and interact with the Eligibility Dashboard.
```
@@ -... @@
-  const isEligibilityStaff = ["master-admin", "admin-support", "eligibility-specialist"].includes(userRole);
+  const isEligibilityStaff = ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(userRole);
```

### `components/app-sidebar.tsx` (modify)
Ensures the Eligibility and Cases navigation items appear in the sidebar for the Case Manager.
```
@@ -... @@
-  const showEligibility = ["master-admin", "admin-support", "eligibility-specialist"].includes(userRole);
+  const showEligibility = ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(userRole);
```

### `tests/auth/middleware-utils.test.ts` (modify)
Updates the test suite to cover the new routing logic for the Case Manager role.
```typescript
@@ -... @@
   it("should return correct default dashboard for internal roles", () => {
     expect(getDefaultDashboardForRole("master-admin")).toBe("/dashboard/cases");
     expect(getDefaultDashboardForRole("admin-support")).toBe("/dashboard/cases");
+    expect(getDefaultDashboardForRole("case-manager")).toBe("/dashboard/cases");
     expect(getDefaultDashboardForRole("eligibility-specialist")).toBe("/dashboard/eligibility");
   });
```

## Test Suggestions

Framework: `Vitest / Jest with React Testing Library`

- **shouldRouteCaseManagerToCasesDashboard** — Verifies that users with the Case Manager role are correctly routed to the cases dashboard upon login.
- **shouldGrantCaseManagerEligibilityAndSupportPermissions** — Verifies that the Case Manager role has the required granular permissions for case and eligibility management.
- **shouldDenyCaseManagerAdminClosureAndPaymentModification** *(edge case)* — Ensures that the Case Manager role is strictly restricted from performing admin closures and modifying payment statuses.
- **shouldRenderCaseActionsForCaseManagerWithoutAdminOptions** — Verifies that the UI correctly enforces the hybrid access of the Case Manager role, showing allowed actions and hiding restricted ones.
- **shouldRenderSidebarNavigationForCaseManager** — Verifies that the sidebar navigation correctly displays the required sections for the Case Manager role.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the current actors (e.g., Internal Staff) and the step-by-step case lifecycle. The new Case Manager role will take over specific actions in Case Creation, Eligibility Review, and Payment Collection, requiring updates to this workflow mapping.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This document outlines the main phases of a case (Eligibility, Payment Collection, Arbitration). The Case Manager role has specific permissions and restrictions within the Eligibility and Payment Collection phases that need to be implemented.

**Suggested Documentation Updates:**

- IDRE Worflow: Needs to be updated to include the new "Case Manager" actor and specify their permissions during Case Creation, Eligibility Review, and Payment Collection, distinguishing them from general "Internal Staff" or "Admin".
- IDRE Case Workflow Documentation: Should be updated to reflect the Case Manager's specific capabilities and restrictions (e.g., cannot perform Admin Closure, cannot mark payments as paid) within the Eligibility and Payment Collection phases.

## AI Confidence Scores
Plan: 95%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._