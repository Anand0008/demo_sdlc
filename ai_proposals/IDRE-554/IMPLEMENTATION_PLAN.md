## IDRE-554: DB: Need to remove refunds 

**Jira Ticket:** [IDRE-554](https://orchidsoftware.atlassian.net//browse/IDRE-554)

## Summary
Create a database script to safely delete 'On Hold' refund records and their allocations for disputes DISP-5032865, DISP-5021984, and DISP-4733285, leaving the cases in their current 'Closed' status.

## Implementation Plan

**Step 1: Create Data Remediation Script for Refund Deletion**  
Create a standalone data remediation script to delete the refund records for the specified disputes. The script must:
1. Initialize `PrismaClient`.
2. Query `prisma.case.findMany` to retrieve the cases where `caseNumber` is in `['DISP-5032865', 'DISP-5021984', 'DISP-4733285']`.
3. For each found case, locate the associated refund records. This involves querying `Payment` records linked to the case (via `CasePaymentAllocation` or direct relation) that match the refund criteria seen in the UI (e.g., `status: 'ON_HOLD'`, `amount: 595`, or `type: 'REFUND'`).
4. Delete the associated `CasePaymentAllocation` records for these payments first to satisfy foreign key constraints.
5. Delete the identified `Payment` records.
6. Query and delete any records in the `CaseRefund` table associated with these cases.
7. Gracefully handle cases where a refund might not exist (e.g., DISP-4733285 as noted in the ticket).
8. Log the IDs of all deleted records to the console for audit purposes.
Files: `scripts/idre-554-remove-refunds.ts`

**Risk Level:** LOW — The change is isolated to a standalone data remediation script targeting specific case numbers. It does not modify application code or database schema. The primary risk is accidentally deleting non-refund payments, which is mitigated by strictly filtering for 'ON_HOLD' refund records and logging deletions.

**Deployment Notes:**
- The script should be executed in the production environment (or via a secure database console) by an authorized engineer.
- A dry-run mode or transaction rollback should be considered during initial execution to verify the correct records are targeted before committing the deletion.

## Proposed Code Changes

### `scripts/idre-554-remove-refunds.ts` (create)
This script fulfills the implementation plan by querying the specified cases, finding their associated 'On Hold' refund payments and allocations, and deleting them in the correct order to respect foreign key constraints. It also cleans up any associated `CaseRefund` records and logs all actions for auditing purposes.
```typescript
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const caseNumbers = ['DISP-5032865', 'DISP-5021984', 'DISP-4733285'];

  console.log(`Starting remediation script for cases: ${caseNumbers.join(', ')}`);

  // 1 & 2. Initialize PrismaClient and query cases
  const cases = await prisma.case.findMany({
    where: {
      caseNumber: {
        in: caseNumbers,
      },
    },
  });

  if (cases.length === 0) {
    console.log('No cases found matching the provided case numbers.');
    return;
  }

  for (const c of cases) {
    console.log(`\nProcessing Case: ${c.caseNumber} (ID: ${c.id})`);

    // 3. Locate associated refund records via CasePaymentAllocation
    const allocations = await prisma.casePaymentAllocation.findMany({
      where: { caseId: c.id },
      include: { payment: true },
    });

    // Match refund criteria (status: ON_HOLD, and type: REFUND or amount: 595)
    const refundAllocations = allocations.filter(
      (allocation) => 
        allocation.payment.status === 'ON_HOLD' && 
        (allocation.payment.type === 'REFUND' || allocation.payment.amount === 595 || allocation.payment.amount === -595)
    );

    // 7. Gracefully handle cases where a refund might not exist
    if (refundAllocations.length === 0) {
      console.log(`  No 'ON_HOLD' refund payments found for case ${c.caseNumber}.`);
    } else {
      for (const allocation of refundAllocations) {
        const paymentId = allocation.paymentId;
        const allocationId = allocation.id;

        console.log(`  Found refund payment to delete: Payment ID ${paymentId}, Allocation ID ${allocationId}`);

        // 4. Delete CasePaymentAllocation first to satisfy foreign key constraints
        await prisma.casePaymentAllocation.delete({
          where: { id: allocationId },
        });
        console.log(`  Deleted CasePaymentAllocation: ${allocationId}`);

        // 5. Delete the identified Payment records
        await prism
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Jest`

- **shouldDeleteOnHoldRefundsAndAllocationsForTargetDisputes** — Verifies that the script correctly identifies 'On Hold' refunds for the target disputes and deletes allocations, refunds, and CaseRefunds in the correct order.
- **shouldNotDeleteRefundsThatAreNotOnHold** *(edge case)* — Verifies that the script ignores refunds that are not in the 'On Hold' status.
- **shouldHandleMissingDisputesGracefully** *(edge case)* — Verifies that the script handles cases where one or more of the target disputes are not found in the database.
- **shouldHandleDatabaseErrorsDuringDeletion** *(edge case)* — Verifies that the script handles database errors gracefully during the deletion process.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._