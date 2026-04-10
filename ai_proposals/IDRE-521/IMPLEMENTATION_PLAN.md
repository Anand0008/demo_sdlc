## IDRE-521: New Role: Case Manager

**Jira Ticket:** [IDRE-521](https://orchidsoftware.atlassian.net//browse/IDRE-521)

## Summary
Implement the 'Case Manager' role by configuring route permissions, updating role helper functions to grant a hybrid of admin-support and eligibility-specialist permissions, and restricting access to admin actions, admin closures, and marking payments as paid in the UI.

## Implementation Plan

**Step 1: Configure Route Permissions for Case Manager**  
Update the `routePermissions` object to ensure `case-manager` is included in the `allowedRoles` array for `/dashboard/cases`, `/dashboard/cases/create`, and `/dashboard/eligibility`. Explicitly ensure `case-manager` is omitted from `/dashboard/admin-closures` and `/dashboard/admin-tools` to enforce the 'No Access to Admin Closure/Actions' constraint.
Files: `lib/auth/route-permissions-config.ts`

**Step 2: Update Role Helpers and Dashboard Permissions**  
Update role helper functions: 1) Ensure `case-manager` is NOT included in `isAdminRole` or `isPaymentRole`. 2) Update `getClientDashboardPermissions` to grant `case-manager` the combined permissions of `admin-support` and `eligibility-specialist` (e.g., `canAssignCases`, `canManageEligibility`, `canAddNotes`, `canManageLineItems`, `canUploadDocuments`, `canRequestRFI`). Ensure `canMarkPaid` and `canPerformAdminActions` evaluate to false for this role.
Files: `lib/auth/client-utils.ts`, `lib/auth/index.ts`

**Step 3: Restrict Payment and Admin Actions in Case Actions UI**  
Update the conditional rendering logic for case actions. Ensure that the 'Mark as Paid' action is strictly gated by `isPaymentRole` or a `canMarkPaid` permission, allowing the `case-manager` to view payments but not mark them as paid. Verify that Admin Actions and Admin Closure buttons are hidden by checking `isAdminRole` or `canPerformAdminActions`.
Files: `components/eligibility/case-actions.tsx`

**Step 4: Enable Specific Case Closures on Eligibility Dashboard**  
Ensure the `case-manager` role can execute case closures during the allowed statuses (Initial Eligibility Review, RFI, Pending Payments, Pending Second Payment, Final Eligibility Review). This may involve ensuring the `userPermissions` passed to `useQuickActions` correctly reflect the ability to close cases without requiring full admin privileges.
Files: `components/eligibility/eligibility-dashboard.tsx`

**Risk Level:** LOW — The `case-manager` role already exists in the base role constants. The required changes are limited to RBAC configuration (route permissions, role helpers) and UI conditional rendering, which carry minimal risk of impacting other existing roles.

**Deployment Notes:**
- Ensure that any cached user sessions or permissions are invalidated or refreshed so that users assigned the `case-manager` role receive the updated permissions immediately.

## Proposed Code Changes

### `lib/auth/route-permissions-config.ts` (modify)
Grants the `case-manager` role access to the cases list, case creation, and the eligibility dashboard. They are intentionally omitted from `/dashboard/admin-closures` and `/dashboard/admin-tools`.
```typescript
--- a/lib/auth/route-permissions-config.ts
+++ b/lib/auth/route-permissions-config.ts
@@ -15,6 +15,7 @@
       "master-admin",
       "admin-support",
       "eligibility-specialist",
+      "case-manager",
       "arbitrator",
       "arbitrator-contractor",
       "payment-admin",
@@ -32,6 +33,7 @@
       "master-admin",
       "admin-support",
       "eligibility-specialist",
+      "case-manager",
     ],
   },
   {
@@ -40,6 +42,7 @@
       "master-admin",
       "admin-support",
       "eligibility-specialist",
+      "case-manager",
     ],
   },
```

### `lib/auth/client-utils.ts` (modify)
Updates the client dashboard permissions to give `case-manager` the combined abilities of `admin-support` (assigning cases) and `eligibility-specialist` (managing eligibility, line items, RFI, and closing cases). Explicitly ensures `canMarkPaid` and `canPerformAdminActions` remain false for this role.
```typescript
--- a/lib/auth/client-utils.ts
+++ b/lib/auth/client-utils.ts
@@ -12,6 +12,7 @@
   const isMasterAdmin = role === "master-admin";
   const isAdminSupport = role === "admin-support";
   const isEligibilitySpecialist = role === "eligibility-specialist";
+  const isCaseManager = role === "case-manager";
   const isPaymentAdmin = role === "payment-admin";
   const isPaymentSpecialist = role === "payment-specialist";
   const isAccounting = role === "accounting";
@@ -25,16 +26,16 @@
   return {
     isAdmin: isMasterAdmin || isCapitolBridgeAdmin,
-    canAssignCases: isMasterAdmin || isAdminSupport || isCapitolBridgeAdmin,
-    canManageEligibility: isMasterAdmin || isEligibilitySpecialist || isCapitolBridgeAdmin,
+    canAssignCases: isMasterAdmin || isAdminSupport || isCaseManager || isCapitolBridgeAdmin,
+    canManageEligibility: isMasterAdmin || isEligibilitySpecialist || isCaseManager || isCapitolBridgeAdmin,
     canAddNotes: true, // All internal roles can add notes
-    canManageLineItems: isMasterAdmin || isEligibilitySpecialist || isCapitolBridgeAdmin,
+    canManageLineItems: isMasterAdmin || isEligibilitySpecialist || isCaseManager || isCapitolBridgeAdmin,
     canUploadDocuments: true, // All internal roles can upload documents
-    canRequestRFI: isMasterAdmin || isEligibilitySpecialist || isCapitolBridgeAdmin,
+    canRequestRFI: isMasterAdmin || isEligibilitySpecialist || isCaseManager || isCapitolBridgeAdmin,
     canMarkPaid: isPaymentAdmin || isPaymentSpecialist || isAccounting || isMasterAdmin,
     canPerformAdminActions: isMasterAdmin || isAdminSupport || isCapitolBridgeAdmin,
-    canCloseCases: isMasterAdmin || isEligibilitySpecialist || isCapitolBridgeAdmin,
+    canCloseCases: isMasterAdmin || isEligibilitySpecialist || isCaseManager || isCapitolBridgeAdmin,
   };
 };
```

### `components/eligibility/case-actions.tsx` (modify)
Ensures that Admin Actions and Admin Closures are strictly hidden from the `case-manager` role, and that "Mark as Paid" is only visible if `canMarkPaid` is true (which is false for `case-manager`).
```
--- a/components/eligibility/case-actions.tsx
+++ b/components/eligibility/case-actions.tsx
@@ -45,8 +45,8 @@
   const { user } = useAuth();
   const permissions = getClientDashboardPermissions(user?.role);
 
-  const showAdminActions = permissions.canPerformAdminActions;
-  const showMarkPaid = permissions.canMarkPaid;
+  const showAdminActions = permissions?.canPerformAdminActions || false;
+  const showMarkPaid = permissions?.canMarkPaid || false;
 
   return (
     <div className="flex flex-wrap gap-2">
@@ -65,7 +65,7 @@
       )}
 
-      {/* Admin Actions */}
-      {showAdminActions && (
+      {/* Admin Actions & Admin Closure */}
+      {showAdminActions && user?.role !== 'case-manager' && (
         <AdminActionsDropdown caseId={caseId} currentStatus={status} />
       )}
```

### `components/eligibility/eligibility-dashboard.tsx` (modify)
Ensures the eligibility dashboard respects the `canCloseCases` permission (which we granted to `case-manager` in `client-utils.ts`) and restricts closures to the allowed statuses specified in the ticket.
```
--- a/components/eligibility/eligibility-dashboard.tsx
+++ b/components/eligibility/eligibility-dashboard.tsx
@@ -85,7 +85,7 @@
   const handleCloseCase = async (caseId: string, method: string) => {
     // Allow closure during specific statuses for authorized roles
     const allowedStatuses = ["Initial Eligibility Review", "RFI", "Pending Payments", "Pending Second Payment", "Final Eligibility Review"];
-    if (!permissions.canCloseCases || !allowedStatuses.includes(currentStatus)) {
+    if (!permissions?.canCloseCases || !allowedStatuses.includes(currentStatus)) {
       toast.error("You do not have permission to close this case at this status.");
       return;
     }
```

### `components/app-sidebar.tsx` (modify)
Updates the sidebar navigation visibility so the `case-manager` can see the Cases and Eligibility tabs, but explicitly hides the Admin Tools tab.
```
--- a/components/app-sidebar.tsx
+++ b/components/app-sidebar.tsx
@@ -42,7 +42,7 @@
   const isEligibility = role === "eligibility-specialist";
+  const isCaseManager = role === "case-manager";
   const isPayment = ["payment-admin", "payment-specialist", "accounting"].includes(role || "");
 
   const navItems = [
     {
       title: "Cases",
       href: "/dashboard/cases",
-      visible: isAdmin || isAdminSupport || isEligibility || isPayment,
+      visible: isAdmin || isAdminSupport || isEligibility || isCaseManager || isPayment,
     },
     {
       title: "Eligibility",
       href: "/dashboard/eligibility",
-      visible: isAdmin || isEligibility,
+      visible: isAdmin || isEligibility || isCaseManager,
     },
     {
       title: "Admin Tools",
       href: "/dashboard/admin-tools",
-      visible: isAdmin || isAdminSupport,
+      visible: (isAdmin || isAdminSupport) && !isCaseManager,
     },
```

### `tests/auth/middleware-utils.test.ts` (modify)
Adds test coverage to ensure the middleware correctly allows and denies access for the new `case-manager` role according to the route permissions configuration.
```typescript
--- a/tests/auth/middleware-utils.test.ts
+++ b/tests/auth/middleware-utils.test.ts
@@ -25,6 +25,12 @@
     expect(checkRouteAccess("/dashboard/cases", "eligibility-specialist")).toBe(true);
+    expect(checkRouteAccess("/dashboard/cases", "case-manager")).toBe(true);
   });
 
   it("should allow case-manager to access eligibility dashboard", () => {
+    expect(checkRouteAccess("/dashboard/eligibility", "case-manager")).toBe(true);
+  });
+
+  it("should deny case-manager access to admin tools", () => {
+    expect(checkRouteAccess("/dashboard/admin-tools", "case-manager")).toBe(false);
+    expect(checkRouteAccess("/dashboard/admin-closures", "case-manager")).toBe(false);
   });
```

## Test Suggestions

Framework: `Jest/Vitest with React Testing Library`

- **should allow case-manager access to eligibility and deny admin routes** — Verifies that the middleware correctly enforces route-level permissions for the new case-manager role.
- **should return correct hybrid permissions for case-manager** — Verifies that the client-utils correctly assign the hybrid permissions to the case-manager role while explicitly denying admin and payment actions.
- **should not render Admin Actions, Admin Closure, or Mark as Paid buttons for case-manager** — Ensures that restricted actions are completely hidden from the UI for case managers.
- **should render Cases and Eligibility tabs but hide Admin Tools for case-manager** — Verifies that the sidebar navigation correctly reflects the case-manager's access levels.
- **should allow case-manager to close cases only in permitted statuses** *(edge case)* — Verifies that case managers can only close cases when they are in the specific allowed statuses defined in the ACs.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Defines the end-to-end case lifecycle and current actors (e.g., Internal Staff). The new Case Manager role will take over specific steps in this workflow and requires explicit permission boundaries.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — Outlines the core phases of the IDRE workflow (Eligibility, Payment Collection, Arbitration) which directly map to the Case Manager's required dashboard access and restricted payment capabilities.

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