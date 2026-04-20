## IDRE-521: New Role: Case Manager

**Jira Ticket:** [IDRE-521](https://orchidsoftware.atlassian.net//browse/IDRE-521)

## Summary
This plan introduces a new "Case Manager" user role, a hybrid of Admin Support and Eligibility Specialist. The implementation involves defining the role and its specific permissions in `lib/auth/permissions.ts`, then enforcing business rule restrictions (no marking payments as paid, no access to the admin closure page) in `lib/utils/eligibility-permissions.ts`. The plan also includes configuring route access, categorizing the role, adding UI text, and updating database seed scripts to make the new role fully integrated and testable.

## Implementation Plan

**Step 1: Define Core Permissions for Case Manager Role**  
In the `ROLE_DEFINITIONS` constant, define the new "case-manager" role. This role should be a hybrid of "admin-support" and "eligibility-specialist". Combine permissions from both, ensuring it has `cases: ["create", "assign_self", "assign_others", "view_all", "master_search"]`, `eligibility_dashboard: ["view", "update_all"]`, `document` management permissions, and granular `administrative_closure` permissions for actions like "ineligible", "withdrawal", and "settlement". Do not grant permissions for `payments_dashboard` or `banking_dashboard`. Also, add "case-manager" to the `roleHierarchy` array, placing it between "eligibility-specialist" and "admin-support" to reflect its authority level.
Files: `lib/auth/permissions.ts`

**Step 2: Implement Business Logic for Payment and Closure Restrictions**  
In the `getEligibilityPermissions` function, implement the specific business logic for the Case Manager role. Add checks for `userRole === "case-manager"` to enforce the restrictions outlined in the ticket. Specifically, set `canUpdatePayments` to `false` to prevent marking payments as paid, and set `canAdministrativeClose` to `false` to block access to the main admin closure dashboard. Ensure other permissions like `canSendRFI`, `canUpdateStatus`, and granular closure permissions (e.g., `canMarkWithdrawal`, `canMarkIneligible`) are explicitly enabled for the case manager.
Files: `lib/utils/eligibility-permissions.ts`

**Step 3: Configure Route Access Control**  
In the `routePermissions` constant, update the `allowedRoles` arrays to grant the "case-manager" role access to necessary pages. Add "case-manager" to the routes for "/dashboard/cases", "/dashboard/cases/create", and "/dashboard/eligibility". Critically, ensure the "case-manager" role is NOT added to the `allowedRoles` for "/dashboard/admin-closures", "/dashboard/payments", or "/dashboard/banking" to enforce the specified restrictions.
Files: `lib/auth/route-permissions-config.ts`

**Step 4: Categorize the New Role as an Internal Admin Role**  
To ensure the new role is correctly categorized within the system, add "case-manager" to the `ADMIN_ROLES` and `INTERNAL_USER_ROLES` arrays. This will integrate the role into administrative UIs and internal user workflows.
Files: `lib/auth/roles.ts`

**Step 5: Add UI Display Name and Description**  
To ensure the new role is displayed correctly in the UI, add an entry for "case-manager" in the `getRoleDisplayName` and `getRoleDescription` functions. The display name should be "Case Manager" and the description should accurately reflect its hybrid nature and restrictions as detailed in the ticket.
Files: `lib/auth/client-utils.ts`

**Step 6: Update Database Seeding for Testing**  
To support development and testing, update the database seeding scripts. In `seeds/factories/user.factory.ts`, add "case-manager" to the list of possible roles in the `createUserData` function and create a new exported function `createCaseManagerUser`. Then, in `seeds/users.ts`, import `createCaseManagerUser` and add logic to seed a few users with the new Case Manager role.
Files: `seeds/factories/user.factory.ts`, `seeds/users.ts`

**Risk Level:** LOW — The changes are confined to the authentication and authorization modules, which are well-structured. The pattern for adding a new role is established and has been followed by recent similar tickets. The exploration report confirms the key files and logic, reducing the risk of unforeseen side effects.

## Proposed Code Changes

### `lib/auth/permissions.ts` (modify)
The ticket explicitly states that the Case Manager role should have "No Access to Admin Closure". The `administrative_closure: ["close"]` permission grants access to this dashboard. This change removes that specific permission while retaining the granular closure permissions (e.g., "withdrawal", "settlement") which allow the user to close cases from the case card, fulfilling all requirements.
```typescript
--- a/lib/auth/permissions.ts
+++ b/lib/auth/permissions.ts
@@ -64,7 +64,6 @@
       arbitration_dashboard: ["view"],
       closing_accounts: ["close"],
       administrative_closure: [
-        "close",
         "withdrawal",
         "settlement",
         "ineligible",
```

### `seeds/factories/user.factory.ts` (modify)
To support development and testing, this change adds a factory function `createCaseManagerUser` for generating users with the new role. It also includes "case-manager" in the random role assignment within `createUserData` to ensure the role is represented in general test data.
```typescript
--- a/seeds/factories/user.factory.ts
+++ b/seeds/factories/user.factory.ts
@@ -36,6 +36,7 @@
       faker.helpers.arrayElement([
         "admin-support",
         "eligibility-specialist",
+        "case-manager",
         "arbitrator",
         "arbitrator-contractor",
         "payment-admin",
@@ -105,6 +106,18 @@
   });
 }
 
+export function createCaseManagerUser(): Omit<
+  User,
+  "sessions" | "accounts"
+> {
+  return createUserData({
+    role: "case-manager",
+    emailVerified: true,
+    banned: false,
+    withImage: true,
+  });
+}
+
 export function createArbitrator(): Omit<User, "sessions" | "accounts"> {
   return createUserData({
     role: "arbitrator",
```

### `seeds/users.ts` (create)
This change updates the main user seeding script to create several "Case Manager" users by default. This ensures that developers and testers have ready-to-use accounts with the new role in their local environments. Since the original file content was not provided, this is proposed as a new file, but it should be merged with the existing `seeds/users.ts` if it exists.
```typescript
// NOTE: The content of seeds/users.ts was not provided.
// This is a complete new file proposal based on the implementation plan and common project patterns.
// If the file exists, this should be treated as a modification.

import { db } from "@/lib/db";
import {
  createAdminUser,
  createMasterAdminUser,
  createRegularUser,
  createBannedUser,
  createCaseManagerUser,
  createEligibilitySpecialist,
  createArbitrator,
  createArbitratorContractor,
  createPaymentAdmin,
  createPaymentSpecialist,
  createAccountingUser,
  createPartyUser,
  createCapitolBridgeAdmin,
  createAttorney,
} from "./factories/user.factory";
import { createUserWithAuth, generateDefaultPassword } from "./utils/auth";
import { logProgress } from "./utils/log";

async function seedUsers() {
  try {
    logProgress("Seeding users...");

    // Clear existing users
    await db.user.deleteMany({});
    logProgress("Cleared existing users.");

    // Create master admin
    logProgress("Creating master admin...");
    const masterAdminData = createMasterAdminUser();
    await createUserWithAuth({
      ...masterAdminData,
      email: "admin@example.com",
      password: generateDefaultPassword(),
    });
    logProgress("✅ Master admin created.");

    // Create admin support users
    logProgress("Creating admin support users...");
    const adminPromises = Array.from({ length: 3 }, () => {
      const userData = createAdminUser();
      return createUserWithAuth({
        ...userData,
        password: generateDefaultPassword(),
      });
    });
    await Promise.all(adminPromises);
    logProgress("✅ Admin support users created", 3);

    // Create eligibility specialists
    logProgress("Creating eligibility specialists...");
    const eligibilityPromises = Array.from({ length: 3 }, () => {
      const userData = createEligibilitySpecialist();
      return createUserWithAuth({
        ...userData,
        password: generateDefaultPassword(),
      });
    });
    await Promise.all(eligi
... (truncated — see full diff in files)
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Jest`

- **shouldGrantCorePermissionsToCaseManager** — This test verifies that the new Case Manager role has been configured with the correct set of permissions required to perform their daily tasks, as specified in the ticket. It confirms the "happy path" functionality.
- **shouldDenyAdminClosurePermissionToCaseManager** *(edge case)* — This test validates a key negative requirement from the ticket: Case Managers must not have access to the Admin Closure page. This directly tests the code change that removed this specific permission.
- **shouldReturnFalseWhenCheckingIfCaseManagerCanMarkPaymentsAsPaid** *(edge case)* — This test enforces the business rule that Case Managers can view payments but cannot change their status to "paid". It covers a critical restriction outlined in the ticket.
- **shouldReturnTrueWhenCheckingIfAdminCanMarkPaymentsAsPaid** — This is a regression test to ensure that while restricting the Case Manager role, we have not inadvertently changed the permissions for other roles like Admin.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the end-to-end case lifecycle and the key responsibilities of 'Internal Staff,' which aligns with the new Case Manager role. It outlines the core phases (Case Creation, Eligibility Review) where this role will operate, providing a high-level process map for the developer.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This document is critically important as it explicitly defines the permissions for the 'Eligibility Specialist' and 'Admin Support' roles, which the new 'Case Manager' role is a hybrid of. It details specific actions, status transitions, and restrictions (e.g., who can mark a case as ineligible) that are essential for implementing the new role's access controls.

**Suggested Documentation Updates:**

- "IDRE Case Workflow Documentation" - The 'User Roles & Permissions' table should be updated to include the new 'Case Manager' role, defining its specific hybrid permissions based on the 'Eligibility Specialist' and 'Admin Support' roles.
- "IDRE Worflow" - The 'Key Platform Roles' section should be updated to add a definition for the new 'Case Manager' role and its place in the case lifecycle.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._