## IDRE-587: DB Change: ReOpen Case

**Jira Ticket:** [IDRE-587](https://orchidsoftware.atlassian.net//browse/IDRE-587)

## Summary
This plan outlines the creation of a one-off database script to reopen two incorrectly closed cases. The script will replicate existing financial cleanup logic from `lib/actions/arbitration.ts` to safely remove associated refunds and payments, then update the case status to `FINAL_DETERMINATION_PENDING` as required. An audit log entry will be created for each case. The script will include a `--dry-run` mode for safety, and no production application code will be modified.

## Implementation Plan

**Step 1: Create New Script File**  
Create a new script file. This script will be a standalone executable for this one-off task and will not be part of the main application runtime. It will contain all logic for finding the cases, cleaning up financial records, and updating the status.
Files: `scripts/idre-587-reopen-incorrectly-closed-cases.ts`

**Step 2: Implement Script Boilerplate and Argument Parsing**  
In the new script, implement the basic structure for a command-line tool. This includes setting up the Prisma client instance, and adding argument parsing for case `disputeReferenceNumber`s and a `--dry-run` flag. Use `scripts/cleanup-closed-case-due-dates.ts` as a reference for the overall structure.
Files: `scripts/idre-587-reopen-incorrectly-closed-cases.ts`

**Step 3: Replicate Financial Cleanup Logic**  
Copy the logic from the `clearNonCompletedRefundArtifacts` function found in `lib/actions/arbitration.ts` into the new script. This logic, which will be wrapped in a Prisma transaction, is responsible for identifying and deleting any `CaseRefund` and associated `Payment` records that are not in a 'COMPLETED' status. This directly addresses the 'Refunds Removed' acceptance criterion. The file `lib/actions/arbitration.ts` will be used for reference only and will not be modified.
Files: `scripts/idre-587-reopen-incorrectly-closed-cases.ts`

**Step 4: Update Case Status and Log Action**  
Within the same Prisma transaction, after the financial cleanup logic, update the `Case` record's `status` field to `FINAL_DETERMINATION_PENDING`. Additionally, create a new `CaseAction` record to provide an audit trail, noting that the case was manually reopened as per ticket IDRE-587.
Files: `scripts/idre-587-reopen-incorrectly-closed-cases.ts`

**Step 5: Execute and Verify Script**  
Execute the script in the target environment using the `--dry-run` flag first to log the intended changes without modifying the database. After verifying the output is correct, run the script without the flag to apply the changes. Manually verify the case statuses and absence of pending refunds in the database afterward.

**Risk Level:** LOW — The risk is low because the change is a one-off data fix performed by a script, not a modification to the application code. The plan includes creating a new, isolated script and incorporating a `--dry-run` mode for verification before any data is changed. The complex logic for financial cleanup is being replicated from existing, tested code.

## Proposed Code Changes

### `scripts/idre-587-reopen-incorrectly-closed-cases.ts` (create)
This new script provides a safe and auditable way to perform the one-off database change required by IDRE-587. It is created in the `scripts/` directory, following project conventions for such tasks. The logic for clearing financial artifacts is carefully replicated from the existing `clearNonCompletedRefundArtifacts` server action to ensure correctness and avoid unintended side effects. The script includes a `--dry-run` mode for safety, argument parsing for specifying target cases, and detailed logging. All database modifications for a given case are wrapped in a transaction to ensure atomicity. A dedicated system user is used for audit log entries, providing a clear record of the script's actions.
```typescript
/**
 * One-off script for IDRE-587 to reopen two incorrectly closed cases.
 *
 * This script will:
 * 1. Identify cases by their disputeReferenceNumber.
 * 2. Delete any associated non-completed refunds and payments.
 * 3. Update the case status to FINAL_DETERMINATION_PENDING.
 * 4. Create an audit log for the changes.
 *
 * Usage:
 *   npx tsx scripts/idre-587-reopen-incorrectly-closed-cases.ts <ref1> <ref2> ... [--dry-run]
 *
 * Example:
 *   npx tsx scripts/idre-587-reopen-incorrectly-closed-cases.ts DISPUTE-REF-123 DISPUTE-REF-456
 *   npx tsx scripts/idre-587-reopen-incorrectly-closed-cases.ts DISPUTE-REF-123 --dry-run
 */

import { PrismaClient, CaseStatus, CaseActionType, Prisma } from "@prisma/client";

const prisma = new PrismaClient();

// A stable user ID for system-initiated actions.
const SCRIPT_USER_ID = "system-script-idre-587";
const SCRIPT_USER_NAME = "System Script (IDRE-587)";

// This function is copied from lib/actions/arbitration.ts
function buildRefundPaymentIdempotencyKey(params: {
  caseId: string;
  partyId: string;
  refundType: string;
  refundReason: string;
}): string {
  return [
    "refund-payment",
    params.caseId,
    params.partyId,
    params.refundType,
    params.refundReason,
  ].join(":");
}

// This function is a modified copy from lib/actions/arbitration.ts `clearNonCompletedRefundArtifacts`
// It's adapted to work within this script.
async function clearNonCompletedRefundArtifacts(
  caseId: string,
  tx: Prisma.TransactionClient
): Promise<{ deletedRefundIds: string[]; deletedPaymentIds: string[] }> {
  const pendingRefunds = await tx.caseRefund.findMany({
    where: {
      caseId,
      status: {
        not: "COMPLETED",
      },
    },
    select: {
      id: true,
      partyId: true,
      refundType: true,
      refundReason: true,
    },
  });

  const pendingRefundIds = pendingRefunds.map((refund) => refund.id);
  const pendingRefundPaymentKeys = pendingRefunds.map((refund) =>
    buildRefundPaymentIdempotencyK
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldUpdateCaseStatusDeleteArtifactsAndCreateAuditLogInLiveMode** — Verifies that when run in live mode, the script correctly deletes financial artifacts, updates the case status, and creates an audit log within a single database transaction.
- **shouldLogIntendedActionsAndNotPerformDbWritesInDryRunMode** — Ensures the --dry-run flag prevents any actual database modifications and instead logs the actions that would have been taken. This is a critical safety feature of the script.
- **shouldThrowErrorIfCaseNotFound** *(edge case)* — Tests the error handling path for when a provided case ID cannot be found, ensuring the script fails gracefully without unintended side effects.
- **shouldSkipExecutionIfCaseIsAlreadyInTheCorrectState** *(edge case)* — Tests the edge case where the script is run against a case that has already been fixed, ensuring it does not perform redundant operations.

## Confluence Documentation References

- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This document provides the explicit business logic for the ticket. It specifies that closed cases can be reopened by an Admin and transitioned to the "FINAL_DETERMINATION_PENDING" status. Crucially, it details the automated financial transactions (Party Refunds, Internal Distributions) that are created upon case closure, which directly relates to the ticket's requirement to have "Refunds Removed".
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page provides a high-level overview of the end-to-end case lifecycle, defining the sequence of statuses from "New" to "Closed". It confirms that the "Determined" status (which is functionally equivalent to "final determination pending") immediately precedes the "Closure" phase, giving context to the state transition requested in the ticket.

**Suggested Documentation Updates:**

- IDRE Case Workflow Documentation

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._