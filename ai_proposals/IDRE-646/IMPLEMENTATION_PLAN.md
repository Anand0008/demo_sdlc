## IDRE-646: Delete Duplicate Refund: DISP-5081506

**Jira Ticket:** [IDRE-646](https://orchidsoftware.atlassian.net//browse/IDRE-646)

## Summary
This implementation plan addresses the task of deleting a duplicate refund by performing a direct database operation. The plan consists of four steps: identifying the specific duplicate payment record ID from the provided information, preparing a deletion script that also handles related records, executing and verifying the script in a staging environment, and finally executing the script in production with a final verification. No application code will be changed as this is a data correction task.

## Implementation Plan

**Step 1: Identify Duplicate Refund Record ID**  
Based on the ticket description and the attached screenshot, identify the primary key of the duplicate refund record. The screenshot highlights an "Overpayment Refund" with status "On Hold" and Payment ID `cmm3s5eau0017ia1mqsyh3100`. Confirm this is the correct record to delete by querying the `Payment` table in the database for case DISP-5081506.

**Step 2: Prepare Deletion Script**  
Prepare a database script to delete the identified payment record. The script must also handle the deletion of any associated records to maintain data integrity. Specifically, it should first delete entries from the `CasePaymentAllocation` table that reference the payment ID, and then delete the record from the `Payment` table itself. The query will be similar to: `DELETE FROM CasePaymentAllocation WHERE paymentId = 'cmm3s5eau0017ia1mqsyh3100'; DELETE FROM Payment WHERE id = 'cmm3s5eau0017ia1mqsyh3100';` Refer to `prisma/schema.prisma` to ensure all foreign key constraints are handled.
Files: `prisma/schema.prisma`

**Step 3: Execute and Verify in Staging Environment**  
Execute the prepared deletion script on a staging environment that has a recent copy of the production data for the affected case. After execution, navigate to the case ledger UI for case DISP-5081506 in staging and verify that the duplicate refund is no longer displayed and that the correct, single refund of $297.50 remains. Check for any unintended side effects on the case's financial data.

**Step 4: Execute in Production and Final Verification**  
After successful verification in the staging environment, schedule and execute the deletion script in the production database. Once the script is run, perform a final verification by checking the case ledger for DISP-5081506 in the production application to confirm the duplicate refund has been removed and the financial summary is correct.

**Risk Level:** MEDIUM — The risk is medium because this plan involves direct manipulation of production database records. While the change is targeted to a single record, any error in the script or identification of the record could lead to incorrect financial data. The risk is mitigated by requiring verification in a staging environment before production execution.

**Deployment Notes:**
- The change is a data fix and does not require a new deployment.
- The deletion script must be run with appropriate database credentials and permissions.

## Proposed Code Changes

### `scripts/data-fixes/IDRE-646-delete-duplicate-refund.ts` (create)
As per the implementation plan, this is a data correction task requiring a direct database operation. Creating a dedicated, one-time script is safer and more maintainable than running raw SQL queries. This script uses the project's existing Prisma ORM to ensure type safety and transactional integrity, first deleting dependent `CasePaymentAllocation` records before deleting the `Payment` record itself. It also includes verification steps to prevent accidental deletion of the wrong data. The new file is placed in a `scripts/data-fixes` directory, which is a logical extension of the existing `scripts` pattern for maintainability.
```typescript
/**
 * @description
 * One-time script to delete a duplicate refund for case DISP-5081506.
 *
 * Ticket: IDRE-646
 * Case Number: DISP-5081506
 * Payment ID to delete: cmm3s5eau0017ia1mqsyh3100
 *
 * This script will:
 * 1. Verify the existence of the case and the target payment.
 * 2. Confirm the payment is allocated to the specified case.
 * 3. Delete the associated CasePaymentAllocation records.
 * 4. Delete the Payment record itself.
 *
 * All deletion operations are performed within a transaction to ensure atomicity.
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

const PAYMENT_ID_TO_DELETE = 'cmm3s5eau0017ia1mqsyh3100';
const CASE_NUMBER = 'DISP-5081506';

async function main() {
  console.log(
    `Starting data fix for ticket IDRE-646: Deleting duplicate refund for case ${CASE_NUMBER}.`,
  );

  try {
    // Step 1: Find the case to get its internal ID for verification.
    const targetCase = await prisma.case.findUnique({
      where: { caseNumber: CASE_NUMBER },
      select: { id: true },
    });

    if (!targetCase) {
      throw new Error(`Case with case number ${CASE_NUMBER} not found.`);
    }
    console.log(`Found case with ID: ${targetCase.id}`);

    // Step 2: Verify the payment to be deleted exists and is linked to the correct case.
    const paymentToDelete = await prisma.payment.findUnique({
      where: { id: PAYMENT_ID_TO_DELETE },
      include: {
        casePaymentAllocations: {
          where: {
            caseId: targetCase.id,
          },
        },
      },
    });

    if (!paymentToDelete) {
      throw new Error(`Payment with ID ${PAYMENT_ID_TO_DELETE} not found.`);
    }

    if (paymentToDelete.casePaymentAllocations.length === 0) {
      throw new Error(
        `Payment ${PAYMENT_ID_TO_DELETE} is not allocated to case ${CASE_NUMBER}. Aborting to prevent accidental deletion.`,
      );
    }

    console.log(
      'Verification successful. Found payment to delete:',
      JSON.string
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Jest`

- **shouldDeleteTheTargetPaymentAndItsAllocations** — Verifies that the script correctly identifies the target payment and its associated allocations, and then deletes them within a single transaction.
- **shouldLogAndAbortIfPaymentNotFound** *(edge case)* — Ensures the script handles the case where the target payment ID is not found in the database and exits gracefully without attempting any deletions.
- **shouldHandleAndLogErrorIfTransactionFails** *(edge case)* — Verifies that if the database transaction fails for any reason (e.g., `deleteMany` fails), the entire operation is rolled back and the error is handled correctly.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page explicitly identifies the "Payments & Refunds Logic / Workflow" as a major complexity hotspot prone to errors that require "hotfixes and manual cleanup." The ticket, which involves manually deleting a duplicate refund, falls directly into this category of work, and this context is crucial for the developer.
- [Delete Data Script Guide](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/271712257) — The ticket requires deleting a specific piece of data (a duplicate refund). This page documents an existing script, `delete_data.py`, designed for this exact purpose, outlining the process, requirements, and expected input format (object ID). This is a directly applicable tool for the developer.

**Suggested Documentation Updates:**

- "Delete Data Script Guide"

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._