## IDRE-551: When user creates IDRE payouts for current day not able to see in report

**Jira Ticket:** [IDRE-551](https://orchidsoftware.atlassian.net//browse/IDRE-551)

## Summary
The user is unable to see IDRE payouts for the current day because the report's API is filtering payments based on a timestamp that is only set after the NACHA generation process. This plan updates the data-fetching logic in both the report API (`app/api/reports/idre-payouts/route.ts`) and the corresponding export API (`app/api/reports/export/route.ts`). The change involves modifying the Prisma query to filter payments by their creation/completion date, rather than a post-processing date, thereby including same-day payouts in the report.

## Implementation Plan

**Step 1: Update IDRE Payouts API query to include same-day payouts**  
In the `GET` function, locate the `prisma.payment.findMany` database query. The `where` clause of this query is likely filtering by a date field that is only populated after the NACHA batch process runs. Modify this condition to filter using the payment's creation or completion date field against the `from` and `to` date variables. This will ensure payouts created on the current day are included in the results before the NACHA process is complete.
Files: `app/api/reports/idre-payouts/route.ts`

**Step 2: Align report export logic with the API change**  
Locate the section within the `POST` function responsible for generating the IDRE Payouts report data for export. This section will contain a Prisma query similar to the one in the main report API. Apply the same logic change to its `where` clause, switching the date filter from a post-processing timestamp to the payment's creation or completion timestamp. This ensures the exported report is consistent with the on-screen data.
Files: `app/api/reports/export/route.ts`

**Risk Level:** LOW — The change is isolated to the data-fetching logic for a single report and its export functionality. It modifies a `where` clause in a read-only query and does not affect any payment processing or data mutation logic. The risk of unintended side effects is minimal.

## Proposed Code Changes

### `app/api/reports/idre-payouts/route.ts` (modify)
The original query filtered payments based on `nachaFile.processedAt`, which meant that payouts only appeared in the report after the NACHA file generation process was complete. This change modifies the query to filter by the payment's `createdAt` field, ensuring that payouts created on the current day are included in the report immediately. The `orderBy` clause has also been updated to sort by `createdAt` for consistency.
```typescript
--- a/app/api/reports/idre-payouts/route.ts
+++ b/app/api/reports/idre-payouts/route.ts
@@ -58,15 +58,9 @@
         direction: 'OUT',
         type: 'IDRE_PAYOUT',
         status: 'COMPLETED',
-        nachaFileId: {
-          not: null,
-        },
-        nachaFile: {
-          processedAt: {
-            gte: from,
-            lte: to,
-          },
+        createdAt: {
+          gte: from,
+          lte: to,
         },
       },
       include: {
@@ -85,9 +79,7 @@
         },
       },
       orderBy: {
-        nachaFile: {
-          processedAt: 'desc',
-        },
+        createdAt: 'desc',
       },
     });
```

### `app/api/reports/export/route.ts` (modify)
This change aligns the report export functionality with the on-screen report API. The Prisma query for fetching IDRE Payouts data for export is updated to filter by `createdAt` instead of `nachaFile.processedAt`. This ensures that the exported CSV file is consistent with the UI and includes same-day payouts that have not yet undergone NACHA processing.
```typescript
--- a/app/api/reports/export/route.ts
+++ b/app/api/reports/export/route.ts
@@ -123,18 +123,12 @@
           direction: 'OUT',
           type: 'IDRE_PAYOUT',
           status: 'COMPLETED',
-          nachaFileId: {
-            not: null,
-          },
-          nachaFile: {
-            processedAt: {
-              gte: fromDate,
-              lte: toDate,
-            },
+          createdAt: {
+            gte: fromDate,
+            lte: toDate,
           },
         },
         include: {
@@ -156,9 +150,7 @@
           },
         },
         orderBy: {
-          nachaFile: {
-            processedAt: 'desc',
-          },
+          createdAt: 'desc',
         },
       });
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldIncludePayoutsCreatedTodayWithoutNachaProcessing** *(edge case)* — This is a regression test to confirm the bug fix. It verifies that the IDRE payouts report API now includes payouts created on the current day, even if they have not yet been processed for NACHA generation.
- **shouldExportPayoutsCreatedTodayWithoutNachaProcessing** *(edge case)* — This test verifies that the fix was also applied to the report export functionality. It ensures that the exported CSV for IDRE Payouts includes same-day payouts that have not yet been processed for NACHA.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page describes the end-to-end case lifecycle, including the "Payment / Accounting" actor. The ticket describes a timing issue with payout reporting, which is directly related to the business process flow defined in this document. Understanding this workflow is necessary to determine when payout data should be considered final and ready for reporting.

**Suggested Documentation Updates:**

- IDRE Worflow

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._