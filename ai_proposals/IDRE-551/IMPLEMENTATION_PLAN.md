## IDRE-551: When user creates IDRE payouts for current day not able to see in report

**Jira Ticket:** [IDRE-551](https://orchidsoftware.atlassian.net//browse/IDRE-551)

## Summary
Fix the IDRE payouts report to include current-day payouts by calculating exact UTC bounds based on the user's local timezone on the frontend and parsing them correctly in the API route.

## Implementation Plan

**Step 1: Update frontend to send local timezone UTC bounds**  
Modify the `fetchPayouts` function to calculate the exact UTC bounds for the selected local dates. Create a local Date object for `fromDate` at `00:00:00` and for `toDate` at `23:59:59.999`. Convert these to UTC ISO strings using `.toISOString()` and pass them as the `from` and `to` query parameters in the API request instead of the raw `YYYY-MM-DD` strings.
Files: `components/reports/idre-payouts-report.tsx`

**Step 2: Update API route to accept and parse ISO datetime strings**  
Update `dateParamSchema` to accept ISO 8601 datetime strings (e.g., using `z.string().datetime()` or updating the regex). Modify the parsing logic to check if `fromParam` and `toParam` contain a time component (e.g., include 'T'). If they do, parse them directly into `Date` objects. Only append `T00:00:00.000Z` and `T23:59:59.999Z` as a fallback if the old `YYYY-MM-DD` format is received.
Files: `app/api/reports/idre-payouts/route.ts`

**Risk Level:** LOW — The changes are isolated to the IDRE payouts report and only affect how date boundaries are calculated and parsed, ensuring current-day records in the user's local timezone are included.

## Proposed Code Changes

### `components/reports/idre-payouts-report.tsx` (modify)
The frontend previously sent raw `YYYY-MM-DD` strings, which the backend parsed as UTC midnight, causing payouts created later in the day in the user's local timezone to be excluded. By calculating the exact start and end of the day in the user's local timezone and converting them to UTC ISO strings, we ensure the entire selected day is covered.
```
--- a/components/reports/idre-payouts-report.tsx
+++ b/components/reports/idre-payouts-report.tsx
@@ -55,7 +55,12 @@
     setLoading(true);
     setError(null);
     try {
-      const response = await fetch(`/api/reports/idre-payouts?from=${fromDate}&to=${toDate}`);
+      // Calculate exact UTC bounds for the selected local dates
+      const fromDateObj = new Date(`${fromDate}T00:00:00`);
+      const toDateObj = new Date(`${toDate}T23:59:59.999`);
+      const fromIso = fromDateObj.toISOString();
+      const toIso = toDateObj.toISOString();
+
+      const response = await fetch(`/api/reports/idre-payouts?from=${encodeURIComponent(fromIso)}&to=${encodeURIComponent(toIso)}`);
       const result: IdrePayoutsResponse = await response.json();
```

### `app/api/reports/idre-payouts/route.ts` (modify)
The API route needs to accept the new ISO datetime strings sent by the frontend. We update the Zod schema to allow an optional time component (`T.*`). When parsing the dates, we check if a time component is present; if so, we use the provided exact UTC time. If not (e.g., when defaulting to today's date in `YYYY-MM-DD` format), we fall back to appending the start and end of the day in UTC.
```typescript
--- a/app/api/reports/idre-payouts/route.ts
+++ b/app/api/reports/idre-payouts/route.ts
@@ -9,7 +9,7 @@
 import { CaseStatus } from "@prisma/client";
 import { z } from "zod";
 
-const dateParamSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format. Expected YYYY-MM-DD.");
+const dateParamSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}(T.*)?$/, "Invalid date format. Expected YYYY-MM-DD or ISO datetime.");
 
 export async function GET(request: NextRequest) {
 
@@ -29,13 +29,17 @@
     const toParsed = dateParamSchema.safeParse(toParam);
     if (!fromParsed.success || !toParsed.success) {
       return NextResponse.json(
-        { error: "Invalid date format. Expected YYYY-MM-DD." },
+        { error: "Invalid date format. Expected YYYY-MM-DD or ISO datetime." },
         { status: 400 }
       );
     }
 
     // Parse dates as full UTC day range to ensure current-day payouts are included
-    const from = new Date(`${fromParsed.data}T00:00:00.000Z`);
-    const to = new Date(`${toParsed.data}T23:59:59.999Z`);
+    const from = fromParsed.data.includes("T")
+      ? new Date(fromParsed.data)
+      : new Date(`${fromParsed.data}T00:00:00.000Z`);
+    const to = toParsed.data.includes("T")
+      ? new Date(toParsed.data)
+      : new Date(`${toParsed.data}T23:59:59.999Z`);
 
     if (isNaN(from.getTime()) || isNaN(to.getTime())) {
```

## Test Suggestions

Framework: `Jest / React Testing Library`

- **should fetch report with exact UTC bounds for local timezone** — Verifies that the frontend calculates and sends exact UTC bounds based on the user's local timezone, fixing the bug where current day payouts were missed.
- **should parse ISO strings with time components correctly** — Verifies that the API route correctly parses the new ISO string format sent by the frontend without overriding the time to UTC midnight.
- **should fallback to UTC midnight when time component is missing** *(edge case)* — Ensures backward compatibility or fallback behavior works correctly when the time component is omitted.

## AI Confidence Scores
Plan: 95%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._