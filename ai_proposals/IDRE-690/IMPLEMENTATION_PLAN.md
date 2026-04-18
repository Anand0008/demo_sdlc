## IDRE-690: After inheriting bank account from Main org to sub org still able to see Exclamation park

**Jira Ticket:** [IDRE-690](https://orchidsoftware.atlassian.net//browse/IDRE-690)

## Summary
This plan resolves a UI bug where an exclamation mark is incorrectly shown for a sub-organization with an inherited bank account. The fix involves updating the `getCaseDetails` server action in `lib/actions/party-case-details.ts`. First, the Prisma query will be modified to fetch the parent organization's banking details along with the sub-organization's. Second, the logic will be updated to check for the parent's bank account if the sub-organization doesn't have one, ensuring the correct status is sent to the UI.

## Implementation Plan

**Step 1: Update Prisma Query to Fetch Parent Organization Bank Info**  
In the `getCaseDetails` function, locate the `prisma.case.findFirst` call. Modify the `include` clause for the party's organization to also fetch its parent organization and the parent's banking details. This will require nesting an `include` for `parentOrganization` within the organization include, and selecting the relevant bank information fields for both the organization and its parent.
Files: `lib/actions/party-case-details.ts`

**Step 2: Implement Logic to Check for Inherited Bank Account**  
After the data is fetched, update the logic that determines if a bank account is configured. The new logic should first check for a bank account on the direct organization. If one is not found, it should then check for a bank account on the `parentOrganization` data that is now being fetched. The resulting status (e.g., a `hasBankAccount` boolean) passed to the frontend should be true if either the organization or its parent has a valid bank account.
Files: `lib/actions/party-case-details.ts`

**Risk Level:** LOW — The change is confined to a single data-fetching action and broadens the condition for a valid bank account setup. It is unlikely to negatively impact organizations that are not in a hierarchy. The primary risk is that other UI locations might use a different data action, which would require a similar fix.

## Proposed Code Changes

### `lib/actions/party-case-details.ts` (modify)
As per the implementation plan, this change addresses the bug in two steps:
1.  The Prisma query within `getCaseDetails` is modified to include the `parentOrganization` and its `PaymentBankInfo` for both the `initiatingPartyOrganization` and `nonInitiatingPartyOrganization`. This ensures the necessary data is available to check for inherited bank accounts.
2.  The logic for constructing the `party` and `counterparty` objects in the return value is updated. The `hasBankAccount` property now correctly evaluates to `true` if either the organization itself or its parent has a `PaymentBankInfo` record, resolving the incorrect display of the warning icon.
```typescript
--- a/lib/actions/party-case-details.ts
+++ b/lib/actions/party-case-details.ts
@@ -101,6 +101,11 @@
             name: true,
             slug: true,
             PaymentBankInfo: true,
+            parentOrganization: {
+              select: {
+                PaymentBankInfo: true,
+              },
+            },
           },
         },
         nonInitiatingPartyOrganization: {
@@ -109,6 +114,11 @@
             name: true,
             slug: true,
             PaymentBankInfo: true,
+            parentOrganization: {
+              select: {
+                PaymentBankInfo: true,
+              },
+            },
           },
         },
       },
@@ -231,7 +241,9 @@
               id: partyOrg.id,
               name: partyOrg.name,
               slug: partyOrg.slug,
-              hasBankAccount: !!partyOrg.PaymentBankInfo,
+              hasBankAccount:
+                !!partyOrg.PaymentBankInfo ||
+                !!partyOrg.parentOrganization?.PaymentBankInfo,
             }
           : null,
       },
@@ -244,7 +256,9 @@
               id: counterpartyOrg.id,
               name: counterpartyOrg.name,
               slug: counterpartyOrg.slug,
-              hasBankAccount: !!counterpartyOrg.PaymentBankInfo,
+              hasBankAccount:
+                !!counterpartyOrg.PaymentBankInfo ||
+                !!counterpartyOrg.parentOrganization?.PaymentBankInfo,
             }
           : null,
       },
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldReturnHasBankAccountTrueForSubOrgWithInheritedBankAccount** — This is the primary regression test. It verifies that if a sub-organization does not have its own bank account but its parent organization does, the `hasBankAccount` flag is correctly set to true.
- **shouldReturnHasBankAccountTrueForOrgWithOwnBankAccount** — Verifies that the logic works correctly for an organization that has its own bank account, ensuring the new logic didn't break the existing happy path.
- **shouldReturnHasBankAccountFalseForOrgWithNoBankAccountAndNoParent** — Verifies the original negative case still works correctly for a standalone organization with no bank account.
- **shouldReturnHasBankAccountFalseForSubOrgAndParentWithNoBankAccount** *(edge case)* — Covers the edge case where an organization is part of a hierarchy but no bank account exists at either level.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD is the primary source of truth for the 'Organization Management' feature. It should contain the specific business rules and acceptance criteria governing how bank account inheritance from a main organization to a sub-organization is supposed to function, including the expected UI state, which is the core of the ticket.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — As a release overview, this page likely contains high-level descriptions, and potentially screenshots or GIFs, of the intended final state of the Organization Management feature. This can provide valuable context for the developer on the expected user experience and correct UI behavior.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview

## AI Confidence Scores
Plan: 85%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._