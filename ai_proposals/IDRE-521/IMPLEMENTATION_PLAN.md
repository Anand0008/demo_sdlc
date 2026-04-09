## IDRE-521: New Role: Case Manager

**Jira Ticket:** [IDRE-521](https://orchidsoftware.atlassian.net//browse/IDRE-521)

## Summary
Refine the permissions for the existing 'case-manager' role to restrict access to Admin Actions, Admin Closures, and marking payments as paid, while ensuring access to standard case management and eligibility functions.

## Implementation Plan

**Step 1: Refine Role Utility Functions for Case Manager**  
Update role utility functions (e.g., `isAdminRole`, `isPaymentRole`, or specific permission checks) to ensure `case-manager` is NOT included in the roles allowed to perform Admin Actions, Admin Closures, or mark payments as paid. Ensure `case-manager` is included in roles allowed to view payments, leave notes, upload documents, and manage RFIs.
Files: `lib/auth/client-utils.ts`, `lib/auth/index.ts`

**Step 2: Restrict Admin Actions and Closures in UI**  
Update the conditional rendering logic for 'Admin Actions' and 'Admin Closure' buttons/menus on the case card to explicitly exclude the `case-manager` role. Ensure standard closure methods remain accessible for the specified statuses.
Files: `components/eligibility/eligibility-dashboard.tsx`, `components/eligibility/case-actions.tsx`

**Step 3: Restrict Mark as Paid Action in UI**  
Update the payment UI components on the case card to allow `case-manager` to view case-specific payments and send for payment collection, but disable or hide the 'Mark as Paid' action for this role.
Files: `components/eligibility/eligibility-dashboard.tsx`, `components/eligibility/case-actions.tsx`

**Risk Level:** LOW — The changes are limited to refining role-based access control (RBAC) checks in the frontend utilities and UI components. Since the role already exists in the configuration, the risk of breaking existing functionality for other roles is low, provided the role checks are updated carefully.

## Proposed Code Changes

### `lib/auth/client-utils.ts` (modify)
Explicitly exclude `case-manager` from `isAdminRole` and `isPaymentRole` to prevent them from performing restricted actions, while adding a `canViewPayments` utility to allow them to see case-specific payments.
```typescript
@@ -...@@
 export const isAdminRole = (role?: string | null) => {
   if (!role) return false;
+  // Case Managers are a hybrid role but should not have full admin privileges
+  if (role === "case-manager") return false;
   return ["master-admin", "admin-support", "capitol-bridge-admin"].includes(role);
 };
 
 export const isPaymentRole = (role?: string | null) => {
   if (!role) return false;
+  // Case Managers can view payments but cannot perform payment role actions (like mark as paid)
+  if (role === "case-manager") return false;
   return ["master-admin", "payment-admin", "payment-specialist", "accounting"].includes(role);
 };
 
+export const canViewPayments = (role?: string | null) => {
+  if (!role) return false;
+  return isPaymentRole(role) || role === "case-manager" || isAdminRole(role);
+};
```

### `lib/auth/index.ts` (modify)
Ensure server-side and core auth utilities explicitly deny Admin Actions and Admin Closure access to the `case-manager` role.
```typescript
@@ -...@@
 export const hasAdminActionsAccess = (role?: string | null) => {
   if (!role) return false;
+  if (role === "case-manager") return false;
   return ["master-admin", "admin-support", "capitol-bridge-admin"].includes(role);
 };
 
 export const hasAdminClosureAccess = (role?: string | null) => {
   if (!role) return false;
+  if (role === "case-manager") return false;
   return ["master-admin", "admin-support", "capitol-bridge-admin"].includes(role);
 };
```

### `components/eligibility/case-actions.tsx` (modify)
Update the conditional rendering logic for 'Admin Actions' and 'Admin Closure' buttons/menus on the case card to explicitly exclude the `case-manager` role.
```
@@ -...@@
   const userRole = session?.user?.role;
 
-  const canPerformAdminActions = isAdminRole(userRole);
-  const canPerformAdminClosure = hasAdminClosureAccess(userRole);
+  const canPerformAdminActions = isAdminRole(userRole) && userRole !== "case-manager";
+  const canPerformAdminClosure = hasAdminClosureAccess(userRole) && userRole !== "case-manager";
 
   return (
     <div className="flex items-center gap-2">
@@ -...@@
```

### `components/eligibility/eligibility-dashboard.tsx` (modify)
Allow `case-manager` to view case-specific payments on the dashboard, but disable or hide the 'Mark as Paid' action for this role.
```
@@ -...@@
   const userRole = session?.user?.role;
 
-  const canMarkAsPaid = isPaymentRole(userRole);
-  const canViewPayments = isPaymentRole(userRole) || isAdminRole(userRole);
+  const canMarkAsPaid = isPaymentRole(userRole) && userRole !== "case-manager";
+  const canViewPayments = isPaymentRole(userRole) || isAdminRole(userRole) || userRole === "case-manager";
 
   return (
@@ -...@@
```

### `components/app-sidebar.tsx` (modify)
Ensure the `case-manager` role can see the Eligibility Dashboard and related navigation items in the sidebar.
```
@@ -...@@
-  const showEligibility = ["master-admin", "admin-support", "eligibility-specialist"].includes(userRole);
+  const showEligibility = ["master-admin", "admin-support", "eligibility-specialist", "case-manager"].includes(userRole);
```

## Test Suggestions

Framework: `Vitest + React Testing Library`

- **should return false for isAdminRole and isPaymentRole when user is case-manager** — Verifies that the case-manager role is explicitly excluded from admin and payment roles in client utilities.
- **should return true for canViewPayments when user is case-manager** — Verifies that the case-manager role is granted permission to view payments.
- **should not render Admin Actions or Admin Closure buttons for case-manager** — Ensures that the UI correctly hides restricted admin actions from the case manager on the case card.
- **should display payments but hide or disable Mark as Paid button for case-manager** — Verifies that case managers can see payments on the dashboard but cannot mark them as paid.
- **should render Eligibility Dashboard navigation link for case-manager** — Ensures the case manager has access to the Eligibility Dashboard from the main application sidebar.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Describes the end-to-end case lifecycle and current actors (Internal Staff) involved in case creation and eligibility, which the new Case Manager role will directly impact and participate in.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — Outlines the core phases of the IDRE workflow (Eligibility, Payment Collection), which are the exact areas the new Case Manager role will be operating within and restricted by.

**Suggested Documentation Updates:**

- IDRE Worflow: Update the Actor Legend and Case Lifecycle table to include the new "Case Manager" role, clarifying their responsibilities for case creation and eligibility review compared to general "Internal Staff".
- IDRE Case Workflow Documentation: Update to reflect the Case Manager's specific permissions and restrictions (e.g., inability to perform Admin Closure or mark payments as paid) during the Eligibility and Payment Collection phases.

## AI Confidence Scores
Plan: 85%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._