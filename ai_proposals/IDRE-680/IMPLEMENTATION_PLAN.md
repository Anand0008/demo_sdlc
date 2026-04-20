## IDRE-680: New Role: VT Director

**Jira Ticket:** [IDRE-680](https://orchidsoftware.atlassian.net//browse/IDRE-680)

## Summary
This plan introduces a new 'VT Director' user role with a specific set of permissions as detailed in the ticket. The work involves defining the new role and its permissions, registering it within the application's role system, granting access to the required UI routes, and adding seeding support to facilitate testing. The changes will be made across the core authentication and authorization configuration files.

## Implementation Plan

**Step 1: Register the 'VT Director' Role**  
Add the new 'vt-director' role to the list of internal user roles and the comprehensive list of all roles to ensure it is recognized throughout the application. This involves updating the `INTERNAL_USER_ROLES` and `ALL_ROLES` constants.
Files: `lib/auth/roles.ts`

**Step 2: Define Role Permissions**  
Define the permissions for the 'VT Director' role. Add a new entry for 'vt-director' in the `ROLE_DEFINITIONS` object. The permissions should be set according to the ticket, granting full access to most resources like cases, payments, banking, and reports, but explicitly excluding permissions for adding or banning users. This will involve listing out specific allowed actions for each resource (e.g., `cases: ['view_all', 'master_search', ...]`).
Files: `lib/auth/permissions.ts`

**Step 3: Update Client-Side Role Utilities**  
Update the client-side utilities to include metadata for the new role. Add a case for 'vt-director' in the `getRoleDisplayName` and `getRoleDescription` functions to ensure the role is displayed correctly in the UI.
Files: `lib/auth/client-utils.ts`

**Step 4: Configure Route Access**  
Grant the 'VT Director' role access to the necessary pages and dashboards. Add 'vt-director' to the `allowedRoles` array for all relevant routes in the `routePermissions` object, including '/dashboard/cases', '/dashboard/payments', '/dashboard/banking', '/dashboard/organizations', '/dashboard/reports', and '/dashboard/cms-invoices'. Do not add it to routes it should not access, like site settings.
Files: `lib/auth/route-permissions-config.ts`

**Step 5: Enable User Seeding for New Role**  
Add the ability to seed 'VT Director' users for testing. In `user.factory.ts`, create a new exported function `createVtDirectorUser` that generates user data with the role set to 'vt-director'. Then, in `users.ts`, import this new factory function and add logic to create at least one 'VT Director' user when the seeding script is run.
Files: `seeds/factories/user.factory.ts`, `seeds/users.ts`

**Risk Level:** LOW — The changes are confined to the authentication and authorization configuration, following established patterns for adding new roles. No complex logic changes are required, and the risk of unintended side effects is low if the permissions are mapped carefully from the ticket's requirements. The addition of a seed user will allow for thorough testing.

## Proposed Code Changes

### `lib/auth/roles.ts` (modify)
This change registers the new `vt-director` role as an internal user role, making it recognizable throughout the application's authentication and authorization systems.
```typescript
--- a/lib/auth/roles.ts
+++ b/lib/auth/roles.ts
@@ -2,6 +2,7 @@
   'master-admin',
   'case-manager',
   'vt-support',
+  'vt-director',
   'billing-admin',
 ] as const;
```

### `lib/auth/permissions.ts` (modify)
This change defines the specific permissions for the new 'VT Director' role within the `ROLE_DEFINITIONS` object, based on the requirements in the Jira ticket. It grants broad access to modules like cases, payments, and banking, while restricting user management capabilities. A new `cms_invoices` permission set is also added to the global `statement` to support full invoice management as required.
```typescript
--- a/lib/auth/permissions.ts
+++ b/lib/auth/permissions.ts
@@ -29,6 +29,13 @@
     "ineligible",
     "resubmission",
     "other",
+  ],
+  cms_invoices: [
+    "view",
+    "create",
+    "update",
+    "delete",
+    "download",
   ],
   payments_dashboard: ["view", "update_all"],
   banking_dashboard: ["view", "update_all"],
@@ -124,6 +131,48 @@
       ],
       document: ["create", "read", "update", "delete", "download"],
     },
+    "vt-director": {
+      users: ["read", "update", "impersonate"],
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
+      administrative_closure: [
+        "close",
+        "withdrawal",
+        "settlement",
+        "ineligible",
+        "resubmission",
+        "other",
+      ],
+      cms_invoices: ["view", "create", "update", "delete", "download"],
+      payments_dashboard: ["view", "update_all"],
+      banking_dashboard: ["view", "update_all"],
+      reports: ["view", "view_all", "view_team", "generate", "export"],
+      organization: ["read", "update", "manage"],
+      document: [
+        "create",
+        "read",
+        "update",
+        "delete",
+        "download",
+        "verify",
+      ],
+    },
     "billing-admin": {
       users: ["read"],
       payments_dashboard: ["view", "update_all"],
```

### `lib/auth/client-utils.ts` (modify)
This updates the client-side utility functions to include a display name and description for the 'VT Director' role, ensuring it is presented correctly in the user interface.
```typescript
--- a/lib/auth/client-utils.ts
+++ b/lib/auth/client-utils.ts
@@ -17,6 +17,8 @@
       return 'Case Manager';
     case 'vt-support':
       return 'VT Support';
+    case 'vt-director':
+      return 'VT Director';
     case 'billing-admin':
       return 'Billing Admin';
     case 'party-admin':
@@ -43,6 +45,8 @@
       return 'Manages cases and related tasks.';
     case 'vt-support':
       return 'Provides support for VT-related issues.';
+    case 'vt-director':
+      return 'Manages VT operations and has broad system access.';
     case 'billing-admin':
       return 'Manages billing and financial information.';
     case 'party-admin':
```

### `lib/auth/route-permissions-config.ts` (modify)
This change grants the 'VT Director' role access to the required dashboard pages by adding it to the `allowedRoles` array for each relevant route, as per the implementation plan.
```typescript
--- a/lib/auth/route-permissions-config.ts
+++ b/lib/auth/route-permissions-config.ts
@@ -1,19 +1,33 @@
 import { RoleName } from './roles';
 
 export const routePermissions: Record<string, { allowedRoles: readonly RoleName[] }> = {
-  '/dashboard': { allowedRoles: ['master-admin', 'case-manager', 'vt-support', 'billing-admin'] },
-  '/dashboard/cases': { allowedRoles: ['master-admin', 'case-manager', 'vt-support'] },
-  '/dashboard/payments': { allowedRoles: ['master-admin', 'billing-admin', 'vt-support'] },
-  '/dashboard/banking': { allowedRoles: ['master-admin', 'billing-admin', 'vt-support'] },
-  '/dashboard/organizations': { allowedRoles: ['master-admin', 'vt-support'] },
-  '/dashboard/reports': { allowedRoles: ['master-admin', 'vt-support'] },
-  '/dashboard/cms-invoices': { allowedRoles: ['master-admin', 'billing-admin'] },
+  '/dashboard': {
+    allowedRoles: ['master-admin', 'case-manager', 'vt-support', 'vt-director', 'billing-admin'],
+  },
+  '/dashboard/cases': {
+    allowedRoles: ['master-admin', 'case-manager', 'vt-support', 'vt-director'],
+  },
+  '/dashboard/payments': {
+    allowedRoles: ['master-admin', 'billing-admin', 'vt-support', 'vt-director'],
+  },
+  '/dashboard/banking': {
+    allowedRoles: ['master-admin', 'billing-admin', 'vt-support', 'vt-director'],
+  },
+  '/dashboard/organizations': { allowedRoles: ['master-admin', 'vt-support', 'vt-director'] },
+  '/dashboard/reports': { allowedRoles: ['master-admin', 'vt-support', 'vt-director'] },
+  '/dashboard/cms-invoices': {
+    allowedRoles: ['master-admin', 'billing-admin', 'vt-director'],
+  },
   '/dashboard/admin/users': { allowedRoles: ['master-admin'] },
   '/dashboard/admin/site-settings': { allowedRoles: ['master-admin'] },
   '/app': { allowedRoles: ['party-admin', 'party-member'] },
   '/app/settings': { allowedRoles: ['party-admin', 'party-member'] },
   '/app/organization': { allowedRoles: ['party-admin'] },
-  '/app/invoices': { allowedRoles: ['party-admin', 'party-me
... (truncated — see full diff in files)
```

### `seeds/factories/user.factory.ts` (modify)
This adds a new factory function, `createVtDirectorUser`, to facilitate the creation of users with the 'VT Director' role for seeding and testing purposes.
```typescript
--- a/seeds/factories/user.factory.ts
+++ b/seeds/factories/user.factory.ts
@@ -37,3 +37,10 @@
     ...overrides,
   });
 }
+
+export function createVtDirectorUser(overrides: Partial<User> = {}): User {
+  return createBaseUser({
+    role: 'vt-director',
+    ...overrides,
+  });
+}
```

### `seeds/users.ts` (modify)
This change updates the database seeding script to create a 'VT Director' user, ensuring that a user with this new role is available in development and testing environments.
```typescript
--- a/seeds/users.ts
+++ b/seeds/users.ts
@@ -4,6 +4,7 @@
   createBaseUser,
   createMasterAdminUser,
   createVtSupportUser,
+  createVtDirectorUser,
 } from './factories/user.factory';
 import { hashPassword } from 'better-auth/utils';
 
@@ -43,6 +44,12 @@
     data: createVtSupportUser({
       email: 'vtsupport@example.com',
     }),
+  });
+
+  await db.user.create({
+    data: createVtDirectorUser({
+      email: 'vtdirector@example.com',
+    }),
   });
 
   // Create party users
```

**New Dependencies:**
- `(No new dependencies needed)`

## Test Suggestions

Framework: `Jest / Vitest`

- **shouldIncludeVtDirectorAsAnInternalRole** — Verifies that the new VT Director role is correctly classified as an internal user role.
- **shouldGrantFullAccessToInvoiceManagementForVtDirector** — Ensures the VT Director role has the expected full access to Invoice Management as per the ticket requirements.
- **shouldDenyAccessToBanUsersForVtDirector** *(edge case)* — Verifies that the VT Director role is explicitly denied permission to ban users, which is a key negative requirement.
- **shouldGrantPartialAccessToImpersonateUsersForVtDirector** — Confirms that the VT Director role has the specified partial access to impersonate users.
- **shouldReturnCorrectDisplayNameAndDescriptionForVtDirector** — Ensures the UI will display the correct, human-readable name and description for the new role.
- **shouldAllowVtDirectorAccessToInvoicesDashboard** — Verifies that the routing configuration correctly grants the VT Director access to a page they are permitted to see.
- **shouldDenyVtDirectorAccessToAdminUsersPage** *(edge case)* — Verifies that the routing configuration correctly denies the VT Director access to a page they are restricted from seeing.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This document is highly relevant as it details the business rules and functionality for the Organization Management System. The ticket grants the 'VT Director' role full access to many of these features, including 'Manage Organization Members', 'Combine Organization', and 'Financial Controls'. A developer will need to consult this PRD to understand the expected behavior of these features before granting permissions.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — The ticket grants the 'VT Director' role full access to 'Cases', 'Eligibility', 'Arbitration', and 'Admin Closures'. This document defines the end-to-end workflow for those processes and lists the actors involved. The developer needs to understand this lifecycle to correctly implement 'full access' permissions for the new role across all stages of a case.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This page confirms the existence of a Role-Based Access Control (RBAC) system and describes the high-level features the new 'VT Director' role will interact with, such as Organization Management, User Impersonation, and Financial Configuration. It provides essential context on the administrative toolset that the new role will have permissions for.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD likely contains a section on user roles and permissions. It should be updated to include the new VT Director role and its specific permissions related to managing organizations.
- IDRE Worflow: The 'Actor Legend' and any role-specific steps in the workflow should be updated to include the VT Director, clarifying its capabilities within the case lifecycle.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: As a high-level guide to admin functions, this page should be updated to describe the new VT Director role and its place within the platform's user hierarchy.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._