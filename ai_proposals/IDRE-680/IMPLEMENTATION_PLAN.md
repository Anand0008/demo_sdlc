## IDRE-680: New Role: VT Director

**Jira Ticket:** [IDRE-680](https://orchidsoftware.atlassian.net//browse/IDRE-680)

## Summary
Implement the new 'VT Director' role by registering it in the role constants, defining its specific permissions (full access to most modules, restricted admin/site settings), configuring route access, and setting up partial access restrictions for user impersonation.

## Implementation Plan

**Step 1: Register VT Director Role**  
Add `"vt-director"` to the `ADMIN_ROLES`, `CAPITOL_BRIDGE_PROTECTED_ROLES`, and `INTERNAL_USER_ROLES` arrays to register the new role in the system.
Files: `lib/auth/roles.ts`

**Step 2: Define Role Permissions**  
Add `"vt-director"` to the `ROLE_DEFINITIONS` object. Grant full access actions to `cases`, `eligibility_dashboard`, `arbitration_dashboard`, `closing_accounts`, `administrative_closure`, `payments_dashboard`, `banking_dashboard`, `reports`, and `document`. For `organization`, grant `["read", "update", "manage"]` but omit `create` and `delete` to prevent adding/banning company admins. Omit `system` entirely to restrict site settings access.
Files: `lib/auth/permissions.ts`

**Step 3: Configure Route Permissions**  
Add `"vt-director"` to the `allowedRoles` array for all relevant routes, including `/dashboard`, `/dashboard/cases`, `/dashboard/eligibility`, `/dashboard/arbitration`, `/dashboard/payments`, `/dashboard/banking`, `/dashboard/nacha`, `/dashboard/cms-invoices`, `/dashboard/reports`, and `/dashboard/admin-closures`.
Files: `lib/auth/route-permissions-config.ts`

**Step 4: Update Client Auth Utilities**  
Integrate `"vt-director"` into client utilities: add it to `roleHierarchy` (e.g., below master-admin), update `getRoleDisplayName` to return `"VT Director"`, update `getRoleDescription`, and ensure `isInternalRole` and `isAdminRole` return true for this role.
Files: `lib/auth/client-utils.ts`

**Step 5: Implement Impersonation Restrictions**  
Add constants and helpers for VT Director impersonation restrictions. Export `isVtDirectorRole(role: string)`, `VT_DIRECTOR_NO_ACCESS_SECTIONS` (containing `['add-banking', 'pay-ach', 'ban-user', 'site-settings', 'org-edit', 'invite-user', 'manage-members']`), and `isVtDirectorNoAccess(section: string)` to enforce partial access rules during impersonation.
Files: `lib/constants/vt-support.ts`

**Risk Level:** LOW — Adding a new role is a standard operation that extends existing RBAC structures without modifying the behavior of existing roles. The changes are isolated to authorization configuration files.

**Deployment Notes:**
- Ensure that any active sessions for users assigned the new 'vt-director' role are refreshed so they pick up the new permissions.

## Proposed Code Changes

### `lib/auth/roles.ts` (modify)
Registers the new `vt-director` role in the core role constants, ensuring it is recognized as an internal admin role and protected from being banned by Capitol Bridge admins.
```typescript
--- lib/auth/roles.ts
+++ lib/auth/roles.ts
@@ -14,7 +14,8 @@
   "appeals-manager",
   "capitol-bridge-admin",
   "attorney",
-  "vt-support"
+  "vt-support",
+  "vt-director"
 ] as const;
 
 /**
@@ -25,6 +26,7 @@
   "payment-specialist",
   "accounting",
   "vt-support",
+  "vt-director",
 ] as const satisfies readonly RoleName[];
 
 /**
@@ -46,7 +48,8 @@
   "appeals-manager",
   "capitol-bridge-admin",
   "attorney",
-  "vt-support"
+  "vt-support",
+  "vt-director"
 ] as const;
 
 /**
```

### `lib/auth/permissions.ts` (modify)
Defines the specific granular permissions for the VT Director role, granting full access to most modules while restricting organization creation/deletion and omitting system/site settings entirely.
```typescript
--- lib/auth/permissions.ts
+++ lib/auth/permissions.ts
@@ -40,6 +40,36 @@
 
 // Role definitions aligned with documentation/roles_and_permissions.csv
 const ROLE_DEFINITIONS = {
+    "vt-director": {
+      cases: [
+        "create",
+        "assign_self",
+        "assign_others",
+        "view_all",
+        "master_search",
+        "close_account",
+      ],
+      eligibility_dashboard: ["view", "update_all"],
+      arbitration_dashboard: [
+        "view",
+        "update_all",
+        "update_assigned",
+        "decide_prevailing_party",
+      ],
+      closing_accounts: ["close"],
+      administrative_closure: [
+        "close",
+        "withdrawal",
+        "settlement",
+        "ineligible",
+        "resubmission",
+        "other",
+      ],
+      payments_dashboard: ["view", "update_all"],
+      banking_dashboard: ["view", "update_all"],
+      reports: ["view", "view_all", "view_team", "generate", "export"],
+      organization: ["read", "update", "manage"],
+      document: ["create", "read", "update", "delete", "download", "verify"],
+    },
     "case-manager": {
       cases: [
         "create",
```

### `lib/auth/route-permissions-config.ts` (modify)
Grants the VT Director role access to the required dashboard routes (cases, eligibility, arbitration, payments, banking, nacha, cms-invoices, reports, admin-closures).
```typescript
--- lib/auth/route-permissions-config.ts
+++ lib/auth/route-permissions-config.ts
@@ -15,6 +15,7 @@
       "appeals-manager",
       "capitol-bridge-admin",
       "vt-support",
+      "vt-director",
       "attorney",
     ],
   },
@@ -28,6 +29,7 @@
       "arbitrator-manager",
       "appeals-manager",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -38,6 +40,7 @@
       "admin-support",
       "view-only",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -49,6 +52,7 @@
       "arbitrator-manager",
       "view-only",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -60,6 +64,7 @@
       "accounting",
       "view-only",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -71,6 +76,7 @@
       "accounting",
       "view-only",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -81,6 +87,7 @@
       "payment-specialist",
       "accounting",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -91,6 +98,7 @@
       "payment-specialist",
       "accounting",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -106,6 +114,7 @@
       "appeals-manager",
       "capitol-bridge-admin",
       "vt-support",
+      "vt-director",
     ],
   },
   {
@@ -116,6 +125,7 @@
       "case-manager",
       "view-only",
       "vt-support",
+      "vt-director",
     ],
   },
```

### `lib/auth/client-utils.ts` (modify)
Integrates the new role into client-side utilities for role hierarchy, display names, descriptions, and boolean checks for internal/admin status.
```typescript
--- lib/auth/client-utils.ts
+++ lib/auth/client-utils.ts
@@ -10,6 +10,7 @@
   "master-admin",
   "capitol-bridge-admin",
   "vt-support",
+  "vt-director",
   "admin-support",
   "payment-admin",
   "payment-specialist",
@@ -40,6 +41,8 @@
       return "Capitol Bridge Admin";
     case "vt-support":
       return "VT Support";
+    case "vt-director":
+      return "VT Director";
     case "admin-support":
       return "Admin Support";
     case "eligibility-specialist":
@@ -76,6 +79,8 @@
       return "Capitol Bridge Administrator";
     case "vt-support":
       return "VT Support Staff";
+    case "vt-director":
+      return "VT Director";
     case "admin-support":
       return "Administrative Support";
     case "eligibility-specialist":
@@ -112,6 +117,7 @@
     "appeals-manager",
     "capitol-bridge-admin",
     "vt-support",
+    "vt-director",
     "attorney",
   ].includes(role);
 }
@@ -132,6 +138,7 @@
     "appeals-manager",
     "capitol-bridge-admin",
     "vt-support",
+    "vt-director",
     "attorney",
   ].includes(role);
 }
```

### `lib/constants/vt-support.ts` (modify)
Adds constants and helper functions to enforce the partial access restrictions for the VT Director role during user impersonation.
```typescript
--- lib/constants/vt-support.ts
+++ lib/constants/vt-support.ts
@@ -21,3 +21,23 @@
 export function isVtSupportNoAccess(section: string): boolean {
   return VT_SUPPORT_NO_ACCESS_SECTIONS.includes(section as VtSupportNoAccessSection);
 }
+
+/**
+ * Sections that VT Director role cannot access during impersonation
+ */
+export const VT_DIRECTOR_NO_ACCESS_SECTIONS = [
+  "add-banking",
+  "pay-ach",
+  "ban-user",
+  "site-settings",
+  "org-edit",
+  "invite-user",
+  "manage-members",
+] as const;
+
+export type VtDirectorNoAccessSection = typeof VT_DIRECTOR_NO_ACCESS_SECTIONS[number];
+
+export function isVtDirectorRole(role?: string | null): boolean {
+  return role === "vt-director";
+}
+
+export function isVtDirectorNoAccess(section: string): boolean {
+  return VT_DIRECTOR_NO_ACCESS_SECTIONS.includes(section as VtDirectorNoAccessSection);
+}
```

## Test Suggestions

Framework: `Vitest`

- **should register vt-director as an internal admin and unbannable role** — Verifies that the VT Director role is properly registered as an internal admin and protected from being banned.
- **should grant correct granular permissions and deny restricted areas to vt-director** — Verifies that the VT Director role has the exact granular permissions specified in the ACs.
- **should allow vt-director access to required dashboard routes and deny site settings** — Verifies that the VT Director role can access the required dashboard routes and is blocked from restricted routes.
- **should return correct display name and internal status for vt-director** — Verifies that client-side utilities correctly identify and format the VT Director role.
- **should enforce partial access restrictions during impersonation for vt-director** *(edge case)* — Verifies the partial access restrictions for the VT Director role during user impersonation.

## AI Confidence Scores
Plan: 95%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._