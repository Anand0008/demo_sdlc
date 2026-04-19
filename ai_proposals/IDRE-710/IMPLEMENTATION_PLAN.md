## IDRE-710: When user is performing admin closure if only IP/NIP paid for dispute status is getting changed to Closed

**Jira Ticket:** [IDRE-710](https://orchidsoftware.atlassian.net//browse/IDRE-710)

## Summary
This plan addresses a bug where a case is prematurely closed during admin closure even if only one of two parties has paid. The fix involves modifying the server action for admin closure, likely located in `lib/actions/payment.ts`, to first verify that both the Initiating and Non-Initiating parties have made their payments. If both have paid, the case will be closed as usual. If not, the case status will be set to `PENDING_ADMINISTRATIVE_CLOSURE` to await the outstanding payment, aligning the system's behavior with the expected workflow. A regression test will be added to ensure this logic is maintained.

## Implementation Plan

**Step 1: Fetch Successful Payment Allocations**  
In the server action responsible for administrative closure, before the `prisma.case.update` call that changes the case status, add logic to fetch all successful payment allocations for the given case. The query should retrieve `paymentAllocations` where the payment status is 'COMPLETED', 'APPROVED', or 'PENDING' and the direction is 'INCOMING'.
Files: `lib/actions/payment.ts`

**Step 2: Verify Payment from Both Parties**  
Using the fetched payment allocations, determine if both the 'INITIATING' and 'NON_INITIATING' parties have paid. Create two boolean flags, `initiatingPartyPaid` and `nonInitiatingPartyPaid`, and set them to true if a corresponding successful payment allocation is found for each party type. The logic found in `lib/actions/party-case-details.ts` between lines 228 and 249 can be used as a direct reference for this check.
Files: `lib/actions/payment.ts`

**Step 3: Conditionally Update Case Status**  
Modify the existing `prisma.case.update` call to be conditional. If both `initiatingPartyPaid` and `nonInitiatingPartyPaid` are true, proceed with setting the case status to the final closed state (e.g., `CLOSED_ADMINISTRATIVE`). If either party has not paid, update the case status to `PENDING_ADMINISTRATIVE_CLOSURE` instead. This prevents the case from being closed prematurely.
Files: `lib/actions/payment.ts`

**Step 4: Add Regression Test Case**  
Add a new test case to a relevant test file, such as `tests/actions/payment-actions.test.ts` (following the pattern of existing files like `tests/actions/case-balance-actions.test.ts`). The test should: 1. Create a case and a successful payment for only one party. 2. Execute the administrative closure action. 3. Assert that the case status is updated to `PENDING_ADMINISTRATIVE_CLOSURE`. 4. Create a payment for the second party and re-trigger the closure logic. 5. Assert that the case status is now updated to `CLOSED_ADMINISTRATIVE`.
Files: `tests/actions/payment-actions.test.ts`

**Risk Level:** LOW — The change is confined to the business logic of a single, specific administrative action. It corrects a deviation from the documented workflow and does not involve database schema changes or modifications to core financial transaction processing. The risk of unintended side effects is minimal.

## Proposed Code Changes

### `lib/actions/payment.ts` (modify)
This change implements the core logic required by the ticket. The `closeCaseAdministratively` server action now fetches all successful incoming payment allocations for the given case. It then checks if payments exist for both the `INITIATING` and `NON_INITIATING` parties. Based on this check, it conditionally sets the case status to either `CLOSED_ADMINISTRATIVE` (if both paid) or `PENDING_ADMINISTRATIVE_CLOSURE` (if one or both have not paid), preventing premature case closure. The `closed_at` timestamp is now only set upon final closure.
```typescript
--- a/lib/actions/payment.ts
+++ b/lib/actions/payment.ts
@@ -1,12 +1,18 @@
 "use server";
 
 import { z } from "zod";
+import {
+  CaseClosureReason,
+  CaseStatus,
+  PartyType,
+} from "@prisma/client";
+
 import { prisma } from "@/lib/database";
 import { auth } from "@/lib/auth/server";
 import { revalidateCaseAndDashboard } from "./cache";
 
 const CloseCaseAdministrativelySchema = z.object({
   caseId: z.string(),
   closureNotes: z.string().optional(),
 });
 
 export async function closeCaseAdministratively(formData: FormData) {
   const session = await auth.getOrThrow();
   const validated = CloseCaseAdministrativelySchema.parse(
     Object.fromEntries(formData.entries())
   );
 
   const { caseId, closureNotes } = validated;
 
-  // This action incorrectly closes the case without verifying payments from both parties.
+  const successfulAllocations = await prisma.casePaymentAllocation.findMany({
+    where: {
+      caseId: caseId,
+      payment: {
+        status: { in: ["COMPLETED", "APPROVED", "PENDING"] },
+        direction: "INCOMING",
+      },
+    },
+    select: {
+      partyType: true,
+    },
+  });
+
+  const initiatingPartyPaid = successfulAllocations.some(
+    (a) => a.partyType === PartyType.INITIATING
+  );
+  const nonInitiatingPartyPaid = successfulAllocations.some(
+    (a) => a.partyType === PartyType.NON_INITIATING
+  );
+
+  const bothPartiesPaid = initiatingPartyPaid && nonInitiatingPartyPaid;
+
+  const newStatus = bothPartiesPaid
+    ? CaseStatus.CLOSED_ADMINISTRATIVE
+    : CaseStatus.PENDING_ADMINISTRATIVE_CLOSURE;
+
+  const updateData: {
+    status: CaseStatus;
+    closure_reason: CaseClosureReason;
+    closure_notes: string | undefined;
+    closed_by_user_id: string;
+    closed_by_role: string;
+    closed_at?: Date;
+  } = {
+    status: newStatus,
+    closure_reason: CaseClosureReason.ADMINISTRATIVE,
+    closure_notes: closureNotes,
+    closed_by_user_id: session.user.id,
+    closed_by_role: session.user.role,

... (truncated — see full diff in files)
```

### `tests/actions/payment-actions.test.ts` (create)
This new test file adds regression tests for the `closeCaseAdministratively` action, as specified in the implementation plan. It covers the primary scenarios: only one party paid, both parties paid, and no parties paid. By mocking the database and authentication dependencies, it ensures the logic within the server action is tested in isolation, verifying that the correct case status and data are set in each situation. This prevents future regressions of the fixed bug.
```typescript
import { closeCaseAdministratively } from "@/lib/actions/payment";
import { prisma } from "@/lib/database";
import { auth } from "@/lib/auth/server";
import {
  CaseClosureReason,
  CaseStatus,
  PartyType,
} from "@prisma/client";

// Mock dependencies
jest.mock("@/lib/database", () => ({
  prisma: {
    case: {
      update: jest.fn(),
    },
    casePaymentAllocation: {
      findMany: jest.fn(),
    },
  },
}));

jest.mock("@/lib/auth/server", () => ({
  auth: {
    getOrThrow: jest.fn(),
  },
}));

jest.mock("@/lib/actions/cache", () => ({
  revalidateCaseAndDashboard: jest.fn(),
}));

const mockedPrisma = prisma as jest.Mocked<typeof prisma>;
const mockedAuth = auth as jest.Mocked<typeof auth>;

describe("Payment Actions - closeCaseAdministratively", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedAuth.getOrThrow.mockResolvedValue({
      user: { id: "test-user-id", role: "ADMIN" },
    } as any);
  });

  it("should set case status to PENDING_ADMINISTRATIVE_CLOSURE if only one party has paid", async () => {
    const formData = new FormData();
    formData.append("caseId", "case-123");
    formData.append("closureNotes", "Admin closing attempt.");

    mockedPrisma.casePaymentAllocation.findMany.mockResolvedValue([
      { partyType: PartyType.INITIATING },
    ]);

    const result = await closeCaseAdministratively(formData);

    expect(mockedPrisma.casePaymentAllocation.findMany).toHaveBeenCalledWith({
      where: {
        caseId: "case-123",
        payment: {
          status: { in: ["COMPLETED", "APPROVED", "PENDING"] },
          direction: "INCOMING",
        },
      },
      select: { partyType: true },
    });

    expect(mockedPrisma.case.update).toHaveBeenCalledWith({
      where: { id: "case-123" },
      data: {
        status: CaseStatus.PENDING_ADMINISTRATIVE_CLOSURE,
        closure_reason: CaseClosureReason.ADMINISTRATIVE,
        closure_notes: "Admin closing attempt.",
        closed_by_user_id: "test-user-id",
        
... (truncated — see full diff in files)
```

**New Dependencies:**
- `No new dependencies needed.`

## Test Suggestions

Framework: `Jest`

- **shouldSetStatusToPendingAdministrativeClosureWhenOnlyOnePartyHasPaid** *(edge case)* — This is the primary regression test. It simulates the exact scenario reported in the bug: an admin attempts to close a case where only one of the two parties has paid. It ensures the fix correctly prevents premature closure.
- **shouldSetStatusToClosedAdministrativeWhenBothPartiesHavePaid** — This test validates the "happy path" scenario. It ensures that when both parties have successfully paid, the administrative closure proceeds as expected, correctly marking the case as closed and recording the closure time.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This is the canonical document describing the end-to-end case lifecycle, including payment collection and closure. It is the primary source for understanding the expected state transitions.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page explicitly identifies that the logic for progressing case statuses based on payments is a known "complexity hotspot" and a source of bugs. It specifically calls out the "Both parties paid vs only one paid" scenario as a key area for QA focus, which directly relates to the ticket's reported issue.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This document provides a high-level overview of the case workflow, defining the key phases like "Payment Collection". It serves as a secondary source to confirm the business process described in the main "IDRE Worflow" page.

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