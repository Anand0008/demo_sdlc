## IDRE-505: DB Change: DISP-4565537 - Adjust Prevailing Party to NIP

**Jira Ticket:** [IDRE-505](https://orchidsoftware.atlassian.net//browse/IDRE-505)

## Summary
Create a one-off database script to fix dispute DISP-4565537 by removing the IP as the prevailing party, deleting the IP's refund, and reverting the case status to Final Determination Pending.

## Implementation Plan

**Step 1: Create database correction script for DISP-4565537**  
Create a standalone executable script using Prisma to correct the dispute DISP-4565537. The script should:
1. Accept an `--apply` flag for dry-run capability.
2. Look up the `Case` by `disputeReferenceNumber` 'DISP-4565537'.
3. Identify the refund `Payment` (and associated `CaseRefund`) for the Initiating Party (IP) and delete them.
4. Update the `ArbitrationDecision` for the case to remove the IP as the prevailing party (e.g., set `awardRecipient` to null or delete the decision record).
5. Update the `Case` status to `CaseStatus.FINAL_DETERMINATION_PENDING`.
6. Execute all database mutations within a `prisma.$transaction` to ensure atomicity.
Files: `scripts/fix-disp-4565537-prevailing-party.ts`

**Risk Level:** LOW — The change is isolated to a single specific case via a targeted script. Using a dry-run mode and a database transaction ensures that the operation can be verified before committing and won't leave the case in a partially updated state.

**Deployment Notes:**
- The script should be executed in the production environment using `npx tsx scripts/fix-disp-4565537-prevailing-party.ts --apply` after verifying the dry-run output.

## Proposed Code Changes

### `scripts/fix-disp-4565537-prevailing-party.ts` (create)
This script fulfills the ticket requirements by targeting the specific dispute (`DISP-4565537`), deleting the incorrect refund and payment records for the Initiating Party, removing the arbitration decision to clear the prevailing party, and reverting the case status to `FINAL_DETERMINATION_PENDING`. It includes a dry-run mode to safely test the logic before applying changes.
```typescript
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const args = process.argv.slice(2);
  const isDryRun = !args.includes("--apply");

  console.log(`Starting fix for DISP-4565537...`);
  if (isDryRun) {
    console.log(`DRY RUN MODE: No changes will be committed. Use --apply to execute.`);
  } else {
    console.log(`APPLY MODE: Changes will be committed to the database.`);
  }

  const disputeReferenceNumber = "DISP-4565537";

  try {
    await prisma.$transaction(async (tx) => {
      // 1. Find the case
      const caseRecord = await tx.case.findUnique({
        where: { disputeReferenceNumber },
        include: {
          parties: true,
          refunds: true,
        },
      });

      if (!caseRecord) {
        throw new Error(`Case with reference ${disputeReferenceNumber} not found.`);
      }

      console.log(`Found case: ${caseRecord.id} (Current status: ${caseRecord.status})`);

      // 2. Identify IP party
      const ipParty = caseRecord.parties.find((p) => p.partyType === "INITIATING_PARTY");
      if (!ipParty) {
        throw new Error("Initiating Party not found for this case.");
      }

      // 3. Find IP refund
      const ipRefunds = caseRecord.refunds.filter((r) => r.partyId === ipParty.id);
      
      for (const refund of ipRefunds) {
        console.log(`Found IP refund to delete: ${refund.id}`);
        
        if (!isDryRun) {
          // Delete CaseRefund first due to foreign key constraints
          await tx.caseRefund.delete({
            where: { id: refund.id },
          });
          
          // Delete associated Payment if it exists
          if (refund.paymentId) {
            await tx.payment.delete({
              where: { id: refund.paymentId },
            });
            console.log(`Deleted associated payment: ${refund.paymentId}`);
          }
        }
      }

      // 4. Remove ArbitrationDecision to clear the prevailing party
      console.log(`Remo
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest or Vitest`

- **shouldNotModifyDatabaseWhenRunningInDryRunMode** — Ensures the script safely logs intended actions without mutating the database when dry-run mode is active.
- **shouldApplyDatabaseFixesWhenDryRunIsDisabled** — Validates the happy path execution of the script, ensuring all three requirements (remove IP prevailing party, remove refund, change status) are executed.
- **shouldExitGracefullyIfDisputeIsNotFound** *(edge case)* — Ensures the script handles the edge case where the target dispute does not exist in the environment being run against.

## Confluence Documentation References

- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — Highlights the complexity and risks associated with manual cleanup of payments, refunds, and status transitions, which is exactly what this DB change entails.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Serves as the canonical reference for the case lifecycle, which is relevant when reverting a case status to 'Final Determination Pending' and adjusting the prevailing party.

## AI Confidence Scores
Plan: 95%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._