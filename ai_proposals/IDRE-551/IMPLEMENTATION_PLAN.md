## IDRE-551: When user creates IDRE payouts for current day not able to see in report

**Jira Ticket:** [IDRE-551](https://orchidsoftware.atlassian.net//browse/IDRE-551)

## Summary
The bug is caused by the frontend `IdrePayoutsReport` component sending a full ISO date string to the backend API, while the API expects a "YYYY-MM-DD" format, causing the date validation to fail. The plan is to correct the date formatting in `components/reports/idre-payouts-report.tsx` before the API call is made. A new test will be added in `tests/app/api/reports-idre-payouts.test.ts` to ensure the backend's date parsing is covered against future regressions.

## Implementation Plan

**Step 1: Correct date format in frontend report component**  
In the `fetchPayouts` function, locate the creation of `URLSearchParams`. Modify the `from` and `to` date values to be formatted as "YYYY-MM-DD" before they are passed to the API. This will involve changing `validatedFrom.toISOString()` to `validatedFrom.toISOString().split("T")[0]` and `validatedTo.toISOString()` to `validatedTo.toISOString().split("T")[0]`. This same change must be applied to the values set in the `appliedFilters` state to ensure the export functionality also uses the correct date format.
Files: `components/reports/idre-payouts-report.tsx`

**Step 2: Add API test for date range filtering**  
Add a new test case to verify that the GET endpoint correctly handles date range parameters. The test should create a request with "from" and "to" search parameters in "YYYY-MM-DD" format. It should then assert that the `prisma.payment.findMany` function is called with the expected `where` clause, specifically checking that the `createdAt` field is queried with `gte` and `lte` properties set to `Date` objects representing the start and end of the provided day(s) in UTC.
Files: `tests/app/api/reports-idre-payouts.test.ts`

**Risk Level:** LOW — The change is confined to the client-side date formatting for a single report and its corresponding export function. The backend logic is already correct and will not be altered. The risk of unintended side effects is minimal.

## Proposed Code Changes

### `components/reports/idre-payouts-report.tsx` (modify)
The API expects dates in "YYYY-MM-DD" format, but the component was sending a full ISO string (e.g., `2023-10-27T12:00:00.000Z`). This caused the backend validation to fail, preventing data from being fetched. This change formats the date correctly before sending it in both the `fetchPayouts` request and when setting `appliedFilters` for the export functionality.
```
--- a/components/reports/idre-payouts-report.tsx
+++ b/components/reports/idre-payouts-report.tsx
@@ -91,16 +91,18 @@
     try {
       const validatedFrom = fromDate!;
       const validatedTo = toDate!;
+      const fromDateString = validatedFrom.toISOString().split("T")[0];
+      const toDateString = validatedTo.toISOString().split("T")[0];
       const params = new URLSearchParams({
-        from: validatedFrom.toISOString(),
-        to: validatedTo.toISOString(),
+        from: fromDateString,
+        to: toDateString,
       });
       const response = await fetch(`/api/reports/idre-payouts?${params}`);
       if (!response.ok) throw new Error("Failed to fetch payouts");
       const data: IdrePayoutsResponse = await response.json();
       if (data.success && data.data) {
         setPayouts(data.data.cases || []);
         setAppliedFilters({
-          from: validatedFrom.toISOString(),
-          to: validatedTo.toISOString(),
+          from: fromDateString,
+          to: toDateString,
           showNewColumns: Boolean(showNewColumns),
         });
         setPage(1);
```

### `tests/app/api/reports-idre-payouts.test.ts` (modify)
This new test case verifies that the API endpoint correctly handles "YYYY-MM-DD" date strings passed as query parameters. It asserts that the `prisma.payment.findMany` function is called with a `where` clause that correctly constructs a full-day UTC date range (`gte` at the start of the day, `lte` at the end), which is crucial for including all records from the specified day(s). This prevents future regressions.
```typescript
--- a/tests/app/api/reports-idre-payouts.test.ts
+++ b/tests/app/api/reports-idre-payouts.test.ts
@@ -1,5 +1,6 @@
 import { describe, it, expect, vi, beforeEach } from "vitest";
 import { NextRequest } from "next/server";
+import { prisma } from "@/lib/database";
 
 // Mock dependencies
 vi.mock("@/lib/auth/server", () => ({
@@ -78,5 +79,36 @@
       expect(data.data).toBeDefined();
       expect(data.data.cases).toBeDefined();
     });
+
+    it("should correctly parse date range parameters and query the database", async () => {
+      const { auth } = await import("@/lib/auth/server");
+      const { GET } = await import("@/app/api/reports/idre-payouts/route");
+
+      vi.mocked(auth.api.getSession).mockResolvedValue({
+        user: { id: "user-1", email: "admin@test.com", role: "payment-admin" },
+        session: { id: "session-1" },
+      } as any);
+
+      const fromDate = "2024-01-15";
+      const toDate = "2024-01-15";
+
+      const request = new NextRequest(
+        `http://localhost/api/reports/idre-payouts?from=${fromDate}&to=${toDate}`
+      );
+
+      await GET(request);
+
+      expect(prisma.payment.findMany).toHaveBeenCalledWith({
+        where: {
+          direction: "OUTGOING",
+          status: "COMPLETED",
+          createdAt: {
+            gte: new Date(`${fromDate}T00:00:00.000Z`),
+            lte: new Date(`${toDate}T23:59:59.999Z`),
+          },
+        },
+        include: expect.any(Object),
+        orderBy: { createdAt: "desc" },
+      });
+    });
   });
 });
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest / Vitest with @testing-library/react`

- **shouldCallApiWithCorrectlyFormattedYyyyMmDdDate** — This is a regression test to confirm the frontend fix. It verifies that the component correctly formats the selected date to 'YYYY-MM-DD' before making the API request, which was the root cause of the bug.
- **shouldCorrectlyParseYyyyMmDdDateAndQueryDatabaseWithFullDayUtcRange** — This regression test validates the backend's date handling logic. It ensures that when the API receives a date in 'YYYY-MM-DD' format, it correctly translates it into a full-day date range for the database query, preventing records from the specified day from being missed.

## Confluence Documentation References

- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This page is relevant because it explicitly mentions ticket IDRE-716, "Not able to generate Nacha File for outcome cases". The Jira ticket IDRE-551 notes that the payout report is unavailable until the NACHA file is generated. This document confirms that NACHA generation is a distinct, recognized process in the platform, providing context for the dependency mentioned in the ticket.

**Suggested Documentation Updates:**

- IDRE Worflow: This page should be updated to clarify the timing dependencies for financial reporting. Specifically, it should state that payout reports for a given day are only populated after the NACHA generation process for that day has been completed.

## AI Confidence Scores
Plan: 100%, Code: 85%, Tests: 100%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._