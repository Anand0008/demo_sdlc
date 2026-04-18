## IDRE-631: Party Portal: Main organization bank account is not getting inherited to sub-organizations

**Jira Ticket:** [IDRE-631](https://orchidsoftware.atlassian.net//browse/IDRE-631)

## Summary
This plan addresses the issue of sub-organizations not inheriting bank accounts from their parent organization. The core of the fix involves modifying the `getCasePaymentHistory` server action in `lib/party-actions.ts` to implement a recursive lookup for a parent's bank account when a sub-organization lacks one. A new test case will be added to `tests/lib/payments/case-ledger.test.ts` to ensure this inheritance logic works as expected.

## Implementation Plan

**Step 1: Implement Bank Account Inheritance Logic in Server Action**  
In `lib/party-actions.ts`, create a new async helper function `getInheritedBankAccounts(organizationId)`. This function will query the database for an organization. If the organization has bank accounts, it will return them. If not, and if a `parentOrganizationId` exists, it will recursively call itself with the parent's ID until it finds an organization with bank accounts or reaches the top of the hierarchy. Then, locate the `getCasePaymentHistory` function and modify it to use this new helper. When processing payment transactions, if the associated organization for a payment does not have a bank account, call `getInheritedBankAccounts` to retrieve the bank account from the nearest parent in the hierarchy. Ensure the `bankInfo` object in the returned transaction data is populated with these inherited details.
Files: `lib/party-actions.ts`

**Step 2: Add Test Case for Bank Account Inheritance**  
In `tests/lib/payments/case-ledger.test.ts`, add a new test suite or test case to validate the bank account inheritance feature. The test setup should include creating a parent organization with a bank account and a child organization without one. Create a case and payment associated with the child organization. The test should then execute the logic that builds the case ledger view model and assert that the bank account information from the parent organization is correctly inherited and present in the transaction details for the child organization.
Files: `tests/lib/payments/case-ledger.test.ts`

**Risk Level:** LOW — The change is confined to server-side data fetching logic for a specific view, with no alterations to the database schema or core UI components. The addition of a dedicated test case will further mitigate the risk of regression or incorrect implementation.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
As per the implementation plan, I've added a new helper function `getInheritedBankAccounts` that recursively traverses up the organization hierarchy to find a bank account. The `getCasePaymentHistory` function is modified to use this helper. It now uses `Promise.all` to handle the asynchronous lookup for each payment, ensuring that if a sub-organization doesn't have a bank account, its parent's is used instead. This directly addresses the ticket's requirement.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -11,7 +11,7 @@
 import { encryptSensitiveData } from "@/lib/encryption";
 
 import { createBulkPayment } from "@/lib/actions/payment";
-import type { PartyType } from "@prisma/client";
+import type { PartyType, BankAccount } from "@prisma/client";
 
 type ActionResult<T = unknown> = {
   success: boolean;
@@ -395,6 +395,43 @@
   return { success: true, data: serializedCase };
 }
 
+/**
+ * Recursively finds bank accounts from an organization or its parents.
+ * @param organizationId The ID of the organization to start from.
+ * @param visited A set to prevent infinite loops in case of cyclic dependencies.
+ * @returns An array of BankAccount objects or null if none are found.
+ */
+async function getInheritedBankAccounts(
+  organizationId: string,
+  visited = new Set<string>()
+): Promise<BankAccount[] | null> {
+  if (!organizationId || visited.has(organizationId)) {
+    return null;
+  }
+  visited.add(organizationId);
+
+  const organization = await prisma.organization.findUnique({
+    where: { id: organizationId },
+    select: {
+      bankAccounts: true,
+      parentOrganizationId: true,
+    },
+  });
+
+  if (!organization) {
+    return null;
+  }
+
+  if (organization.bankAccounts && organization.bankAccounts.length > 0) {
+    return organization.bankAccounts;
+  }
+
+  if (organization.parentOrganizationId) {
+    return getInheritedBankAccounts(organization.parentOrganizationId, visited);
+  }
+
+  return null;
+}
+
 export async function getCasePaymentHistory(caseId: string) {
   try {
     const { user } = await auth();
@@ -505,13 +542,23 @@
       };
     });
 
-    const transactions = payments.map((payment) => {
-      const bankInfo =
-        payment.organization?.bankAccounts?.[0] ??
-        payment.paymentMethod?.bankAccount ??
-        null;
-
-      return {
+    const transactions = await Promise.all(
+      payments.map(async (payment) => {
+        let bankAccounts = payment.or
... (truncated — see full diff in files)
```

### `tests/lib/payments/case-ledger.test.ts` (modify)
This change adds a new test suite to validate the bank account inheritance logic, as specified in the implementation plan. The test creates a parent organization with a bank account and a child organization without one. It then verifies that a payment made by the child organization correctly displays the parent's bank account details in the payment history, ensuring the new logic works as expected.
```typescript
--- a/tests/lib/payments/case-ledger.test.ts
+++ b/tests/lib/payments/case-ledger.test.ts
@@ -1,5 +1,8 @@
 import { describe, it, expect, beforeAll, afterAll } from "vitest";
 import { prisma } from "@/lib/database";
+import { Prisma } from "@prisma/client";
+import { getCasePaymentHistory } from "@/lib/party-actions";
+
 // ... other imports
 
 describe("Case Ledger", () => {
@@ -8,3 +11,64 @@
   // ... existing tests
 });
 
+// Add new describe block at the end of the file
+describe("getCasePaymentHistory with organization hierarchy", () => {
+  it("should inherit bank account from parent organization for a payment", async () => {
+    // Arrange: Create a parent org with a bank account
+    const parentOrg = await prisma.organization.create({
+      data: {
+        name: "Parent Corp Test",
+        type: "COMPANY",
+        slug: `parent-corp-test-${Date.now()}`,
+      },
+    });
+    const parentBankAccount = await prisma.bankAccount.create({
+      data: {
+        organizationId: parentOrg.id,
+        accountHolderName: "Parent Corp Inc.",
+        accountNumberLast4: "1234",
+        bankName: "First National",
+        routingNumber: "111000025",
+        isVerified: true,
+      },
+    });
+
+    // Arrange: Create a child org without a bank account
+    const childOrg = await prisma.organization.create({
+      data: {
+        name: "Child LLC Test",
+        type: "COMPANY",
+        slug: `child-llc-test-${Date.now()}`,
+        parentOrganizationId: parentOrg.id,
+      },
+    });
+
+    // Arrange: Create a case and a payment associated with the child org
+    const case_ = await prisma.case.create({
+      data: {
+        status: "OPEN",
+        initiatingPartyType: "INDIVIDUAL",
+        nonInitiatingPartyType: "ORGANIZATION",
+        nonInitiatingPartyOrganizationId: childOrg.id,
+      },
+    });
+    const payment = await prisma.payment.create({
+      data: {
+        caseId: case_.id,
+        organizationId: childOrg.id,
+        am
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Jest`

- **shouldInheritBankAccountFromDirectParentWhenSubOrganizationHasNone** — This is the primary regression test to verify that a sub-organization without a bank account correctly inherits the one from its immediate parent. It directly validates the fix for the reported bug.
- **shouldUseOwnBankAccountWhenAvailableAndNotInherit** — This test ensures that the inheritance logic does not incorrectly override a bank account that is explicitly set on a sub-organization.
- **shouldInheritBankAccountFromGrandparentWhenParentHasNone** *(edge case)* — This test covers the edge case of multi-level inheritance, ensuring the recursive lookup works correctly past the immediate parent.
- **shouldReturnNullWhenNoBankAccountExistsInHierarchy** *(edge case)* — This test covers the boundary condition where no bank account exists in the entire organizational hierarchy, ensuring the function terminates gracefully.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the Organization Management System, which is the parent feature (IDRE-319) of this ticket. It is the most authoritative source for business rules regarding how parent and sub-organizations should function, including data inheritance logic for attributes like bank accounts.

**Suggested Documentation Updates:**

- "Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be updated to explicitly state the implemented bank account inheritance logic for sub-organizations, ensuring the business rule is formally captured."

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._