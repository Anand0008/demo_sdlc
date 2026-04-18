## IDRE-623: Party Portal: Filter functionality not working as expected

**Jira Ticket:** [IDRE-623](https://orchidsoftware.atlassian.net//browse/IDRE-623)

## Summary
This plan addresses a bug where the organization filter on the "Pay Online" page is not working correctly. The fix involves updating the backend server action in `lib/party-actions.ts` to properly use the provided `organizationId` in its database query to filter cases. A corresponding check in `app/app/payments/page.tsx` will ensure the selected organization ID from the UI is passed to this updated backend function.

## Implementation Plan

**Step 1: Update server action to filter cases by organization ID**  
Locate the `getPartyCases` function (or the function aliased as `getCasesForPayment` used by the payments page). Modify its signature to accept an optional `organizationId` string parameter. Inside the function, update the `prisma.case.findMany` query. If a valid `organizationId` is provided (i.e., not null or 'all'), add a condition to the main `where` clause to filter the results. The condition should ensure that only cases where either the `initiatingPartyOrganizationId` or `nonInitiatingPartyOrganizationId` matches the provided `organizationId` are returned.
Files: `lib/party-actions.ts`

**Step 2: Ensure organization ID is passed from page to server action**  
In the `PaymentsPage` component, locate the call to the case-fetching server action (`getPartyCases` or `getCasesForPayment`). Ensure that the `activeOrganizationId` variable, which is derived from the `organizationId` search parameter, is correctly passed to the server action. This will connect the frontend filter selection to the updated backend logic.
Files: `app/app/payments/page.tsx`

**Risk Level:** LOW — The change is confined to a single data-fetching function and its corresponding call on the page. The modification adds a filter condition, which is unlikely to have unintended side effects on other parts of the application. The risk of regression is low as it corrects a specific filtering bug.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
The core of the bug lies here. The `getCasesForPayment` function, which fetches cases for the payments page, was not considering the `organizationId`. I've updated its signature to accept an `organizationId` and added logic to conditionally modify the Prisma query. If an `organizationId` is provided, it now filters cases where the organization is either the initiating or non-initiating party. I also updated the `fetchMoreCasesForPayment` wrapper to accept and pass through the `organizationId`, ensuring pagination also respects the filter.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -1,12 +1,14 @@
 "use server";
 
 import { revalidatePath } from "next/cache";
 import { z } from "zod";
 import { prisma } from "@/lib/prisma";
 import { getCurrentSession } from "@/lib/auth/utils";
 import { Prisma } from "@prisma/client";
 
 export async function getCasesForPayment({
   page = 1,
   limit = 25,
+  organizationId,
 }: {
   page?: number;
   limit?: number;
+  organizationId?: string | null;
 }) {
   const session = await getCurrentSession();
   if (!session?.user?.partyId) {
@@ -22,6 +24,19 @@
     ],
   };
 
+  if (organizationId) {
+    where.AND = [
+      ...(Array.isArray(where.AND) ? where.AND : []),
+      {
+        OR: [
+          { initiatingPartyOrganizationId: organizationId },
+          { nonInitiatingPartyOrganizationId: organizationId },
+        ],
+      },
+    ];
+  }
+
   try {
     const [cases, total] = await prisma.$transaction([
       prisma.case.findMany({
@@ -51,10 +66,16 @@
 
 export async function fetchMoreCasesForPayment({
   page = 1,
   limit = 25,
+  organizationId,
 }: {
   page?: number;
   limit?: number;
+  organizationId?: string | null;
 }) {
-  return getCasesForPayment({ page, limit });
+  return getCasesForPayment({ page, limit, organizationId });
 }
 
 export async function downloadCasesForPaymentCsv() {
```

### `app/app/payments/page.tsx` (modify)
This change connects the frontend filter selection to the updated backend logic for the initial page load. The `activeOrganizationId`, derived from the URL search parameters, is now passed to the `getCasesForPayment` server action.
```
--- a/app/app/payments/page.tsx
+++ b/app/app/payments/page.tsx
@@ -58,7 +58,7 @@
   // Using paginated fetch to avoid Lambda timeout for large organizations.
   const [initialCasesResult, bankAccounts] = await Promise.all([
-    getCasesForPayment({ page: 1 }),
+    getCasesForPayment({ page: 1, organizationId: activeOrganizationId }),
     getUserBankAccounts(),
   ]);
```

### `app/app/payments/components/payment-form.tsx` (modify)
To ensure the organization filter persists during pagination, this change is necessary. I've added the `useSearchParams` hook to get the current `organizationId` from the URL and pass it to the `fetchMoreCasesForPayment` action when loading more cases. This prevents the filter from being dropped after the first page.
```
--- a/app/app/payments/components/payment-form.tsx
+++ b/app/app/payments/components/payment-form.tsx
@@ -1,6 +1,6 @@
 "use client";
 
 import { useState, useCallback, useEffect, useMemo, useRef } from "react";
-import { useRouter } from "next/navigation";
+import { useRouter, useSearchParams } from "next/navigation";
 import { useForm } from "react-hook-form";
 import { zodResolver } from "@hookform/resolvers/zod";
 import { z } from "zod";
@@ -73,6 +73,7 @@
   const [isSubmitting, setIsSubmitting] = useState(false);
   const [isLoadingMore, setIsLoadingMore] = useState(false);
   const router = useRouter();
+  const searchParams = useSearchParams();
   const form = useForm<z.infer<typeof paymentFormSchema>>({
     resolver: zodResolver(paymentFormSchema),
     defaultValues: {
@@ -210,10 +211,11 @@
     if (!hasMorePages || isLoadingMore) return;
     setIsLoadingMore(true);
     try {
+      const organizationId = searchParams.get("organizationId");
       const nextPage = currentPage + 1;
       const result = await fetchMoreCasesForPayment({
         page: nextPage,
-        limit: 25, // Assuming a page size
+        organizationId,
       });
 
       if (result.error) {
@@ -227,7 +229,7 @@
     } finally {
       setIsLoadingMore(false);
     }
-  }, [currentPage, hasMorePages, isLoadingMore, cases, setCases]);
+  }, [currentPage, hasMorePages, isLoadingMore, cases, setCases, searchParams]);
 
   const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
     const value = e.target.value;
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest/Vitest`

- **shouldFilterCasesByOrganizationIdWhenProvided** — This is a regression test for the bug fix. It verifies that when an `organizationId` is provided, the server action correctly builds the database query to filter cases belonging to that organization.
- **shouldPassOrganizationIdToFetchMoreCasesWhenPaginating** — This test ensures the client-side component correctly reads the organization filter from the URL and passes it to the server action during pagination, preventing the filter from being dropped after the first page.
- **shouldNotAddFilterWhenOrganizationIdIsMissing** *(edge case)* — This test covers the edge case where no organization filter is applied. It ensures that the function's behavior remains correct for the default, unfiltered view, preventing a regression.
- **shouldPassOrganizationIdToGetCasesForPaymentOnInitialLoad** — This test verifies that the initial page load correctly uses the organization filter from the URL. It ensures the first set of data displayed to the user is already filtered.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the exact feature the ticket is addressing. It is the primary source of truth for business rules and expected behavior of the organization management system, including how filtering should function. A developer must read this to understand the intended logic before attempting a fix.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview explains the functionality of the Organization Management tools. It provides context on the user-facing aspects of the feature, such as the relationship between users, organizations, and cases, which is directly relevant to fixing a data visibility bug in the filter.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be reviewed to ensure the filtering logic implemented in the bug fix aligns with the specified requirements. If any ambiguity in the requirements led to the bug, the document should be clarified.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: As this is a user-facing overview, it should be checked for accuracy after the bug is fixed to ensure it correctly describes the filtering behavior.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._