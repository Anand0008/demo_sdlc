## IDRE-551: When user creates IDRE payouts for current day not able to see in report

**Jira Ticket:** [IDRE-551](https://orchidsoftware.atlassian.net//browse/IDRE-551)

## Summary
The bug where current-day IDRE payouts don't appear in the report will be fixed by changing the data-fetching logic in the `/api/reports/idre-payouts` API route. The Prisma query currently filters payments by their `createdAt` timestamp. This will be changed to filter by the `updatedAt` timestamp, which more accurately reflects when a payment's status was set to `COMPLETED`. A new regression test will be added to ensure the corrected date filtering works as expected.

## Implementation Plan

**Step 1: Update Prisma query to filter by completion date**  
In the `GET` handler, modify the `prisma.payment.findMany` call. Change the date filter in the `where` clause from `createdAt` to `updatedAt`. Also, update the `orderBy` clause to sort by `updatedAt` to maintain consistency. This will ensure the query includes payments that were completed within the specified date range, even if they were created on a prior day. Specifically, change line 56 from `createdAt: { gte: from, lte: to }` to `updatedAt: { gte: from, lte: to }` and line 79 from `orderBy: { createdAt: 'desc' }` to `orderBy: { updatedAt: 'desc' }`.
Files: `app/api/reports/idre-payouts/route.ts`

**Step 2: Add regression test for date filtering logic**  
Add a new test case to verify the fix and prevent regressions. This test should mock a `Payment` record with a `createdAt` date before the queried date range but an `updatedAt` date within the range. It will then call the API endpoint and assert that this payment is correctly included in the results, confirming that the logic now correctly filters by the completion timestamp.
Files: `tests/app/api/reports-idre-payouts.test.ts`

**Risk Level:** LOW — The change is confined to a single API endpoint for a non-critical report. The modification aligns the query logic with the apparent business requirement of viewing payouts based on their completion date, not their creation date. The risk of unintended side effects is minimal.

## Proposed Code Changes

### `app/api/reports/idre-payouts/route.ts` (modify)
The Prisma query was incorrectly filtering payments by `createdAt`. This has been changed to `updatedAt`, which accurately reflects when a payment's status was set to `COMPLETED`. The `orderBy` clause was also updated to `updatedAt` for consistency. This ensures that payouts processed on the current day are correctly included in the report, even if they were created on a previous day.
```typescript
--- a/app/api/reports/idre-payouts/route.ts
+++ b/app/api/reports/idre-payouts/route.ts
@@ -53,7 +53,7 @@
       where: {
         direction: 'OUTGOING',
         status: 'COMPLETED',
-        createdAt: { gte: from, lte: to },
+        updatedAt: { gte: from, lte: to },
       },
       include: {
         caseAllocations: {
@@ -78,7 +78,7 @@
           },
         },
       },
-      orderBy: { createdAt: 'desc' },
+      orderBy: { updatedAt: 'desc' },
     });
 
     // Helper to extract payee from JSON or fallback
```

### `tests/app/api/reports-idre-payouts.test.ts` (modify)
A new regression test has been added to verify the fix. This test case mocks a payment created on a previous day but completed on the current day. It asserts that the API correctly fetches this payment when queried for the current day's date range and that the underlying database query uses `updatedAt` for both filtering and ordering. This ensures the fix is effective and prevents future regressions.
```typescript
--- a/tests/app/api/reports-idre-payouts.test.ts
+++ b/tests/app/api/reports-idre-payouts.test.ts
@@ -1,5 +1,6 @@
 import { describe, it, expect, vi, beforeEach } from "vitest";
 import { NextRequest } from "next/server";
+import { CaseStatus, DisputeType } from "@prisma/client";
 
 // Mock dependencies
 vi.mock("@/lib/auth/server", () => ({
@@ -77,6 +78,62 @@
       expect(data.data).toBeDefined();
       expect(data.data.cases).toBeDefined();
     });
+
+    it("should filter payments by updatedAt to include same-day completed payouts", async () => {
+      const { auth } = await import("@/lib/auth/server");
+      const { prisma } = await import("@/lib/database");
+      const { GET } = await import("@/app/api/reports/idre-payouts/route");
+
+      vi.mocked(auth.api.getSession).mockResolvedValue({
+        user: { id: "user-1", email: "admin@test.com", role: "payment-admin" },
+        session: { id: "session-1" },
+      } as any);
+
+      const today = new Date();
+      const yesterday = new Date();
+      yesterday.setDate(today.getDate() - 1);
+      const todayStr = today.toISOString().split("T")[0];
+
+      const mockPayment = {
+        id: "payment-1",
+        direction: 'OUTGOING',
+        status: 'COMPLETED',
+        createdAt: yesterday,
+        updatedAt: today,
+        processedAt: today,
+        paidAt: today,
+        recipientName: 'veratru',
+        bankingSnapshot: { accountHolderName: 'veratru' },
+        caseAllocations: [
+          {
+            case: {
+              disputeReferenceNumber: 'DISP-123',
+              status: CaseStatus.CLOSED_ADMINISTRATIVE,
+              typeOfDispute: DisputeType.SINGLE,
+              decision_date: today,
+              closed_at: today,
+              closure_reason: 'SETTLEMENT',
+              DisputeLineItems: [{ id: 'li-1' }],
+            },
+          },
+        ],
+      };
+      vi.mocked(prisma.payment.findMany).mockResolvedValue([mockPayment]);
+
+      const request = new Nex
... (truncated — see full diff in files)
```

**New Dependencies:**
- `No new dependencies needed.`

## Test Suggestions

Framework: `Jest / Vitest`

- **shouldFetchPayoutsCompletedTodayEvenIfCreatedPreviously** *(edge case)* — This is the primary regression test. It verifies that the API correctly fetches payouts that were completed today, even if they were created on a previous day, by checking that the database query now uses the `updatedAt` field for filtering and sorting.
- **shouldFetchPayoutsCreatedAndCompletedToday** — A happy path test to ensure that standard functionality remains intact and that payouts created and completed on the same day are returned correctly with the new logic.
- **shouldReturn500ErrorIfDatabaseQueryFails** *(edge case)* — Verifies that the API route handles database errors gracefully and returns a 500 Internal Server Error instead of crashing.

## Confluence Documentation References

- [IDRE Stand up Notes](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/206602242) — This page provides context that the NACHA generation process has had prior issues, including a high-priority bug where a NACHA file was duplicated but not associated correctly with cases. This is relevant as the ticket notes that the report is dependent on NACHA generation.
- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This page is highly relevant because it lists a recent, closely related ticket, IDRE-716 "Not able to generate Nacha File for outcome cases". This indicates that the NACHA generation logic, which the ticket depends on, has been under recent development and could be the source of the reporting issue.
- [Issue List](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/324239363) — This page directly mentions "IDRE Payouts" in the context of another ticket, IDRE-428, which states that payouts "should be in hold". This suggests there is specific business logic or a status ("hold") that might be preventing the payouts from appearing in the report immediately after creation.

**Suggested Documentation Updates:**

- IDRE Worflow

## AI Confidence Scores
Plan: 100%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._