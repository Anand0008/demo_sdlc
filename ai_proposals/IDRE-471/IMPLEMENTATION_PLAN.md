## IDRE-471: Application Error: a client-side exception has occurred.

**Jira Ticket:** [IDRE-471](https://orchidsoftware.atlassian.net//browse/IDRE-471)

## Summary
Fix the client-side exception in the banking dashboard by adding safe property access (optional chaining) and default array values in the BankingClient component, ensuring safe data passing from the server, and implementing a local Error Boundary to gracefully handle any future rendering errors.

## Implementation Plan

**Step 1: Add safe property access and fallbacks in BankingClient**  
Update the `BankingClient` component to use optional chaining (`?.`) for all nested property accesses (e.g., `payment.organization?.name`, `payment.case?.title`, `payment.bankAccount?.accountNumber`). Ensure that any array props (like `payments`) default to an empty array (`[]`) to prevent `.map()` errors. Verify that any Date objects are safely converted to strings before rendering.
Files: `app/dashboard/banking/banking-client.tsx`

**Step 2: Ensure safe data passing in BankingPage**  
Update the data fetching logic in `BankingDataFetcher` to ensure that the data passed to `BankingClient` is properly serialized and defaults to an empty array if the fetch function (`getApprovedPayments`) returns undefined or an error.
Files: `app/dashboard/banking/page.tsx`

**Step 3: Add Error Boundary for the Banking module**  
Create a new `error.tsx` file in the `app/dashboard/banking` directory. Implement a Next.js Error Boundary component that catches unhandled exceptions in the banking module and displays a user-friendly error message with a 'Try again' button, preventing the generic application crash screen.
Files: `app/dashboard/banking/error.tsx`

**Risk Level:** LOW — The changes involve adding safe navigation operators, default values, and an error boundary, which are non-destructive and improve application resilience without altering core business logic.

**Deployment Notes:**
- Ensure that the new error.tsx file is correctly picked up by the Next.js App Router to handle errors in the banking segment.

## Proposed Code Changes

### `app/dashboard/banking/error.tsx` (create)
Implements a local Next.js Error Boundary for the banking module to gracefully catch any unhandled rendering errors and prevent the entire application from crashing, providing a user-friendly recovery option.
```
"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export default function BankingError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error("Banking module error:", error);
  }, [error]);

  return (
    <div className="flex h-[50vh] w-full items-center justify-center p-4">
      <Card className="w-full max-w-md border-destructive/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <CardTitle>Something went wrong</CardTitle>
          </div>
          <CardDescription>
            An error occurred while loading the banking dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground break-words">
            {error.message || "A client-side exception has occurred."}
          </p>
        </CardContent>
        <CardFooter>
          <Button onClick={() => reset()} variant="default" className="w-full">
            Try again
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
```

### `app/dashboard/banking/page.tsx` (modify)
Wraps the data fetching logic in a try-catch block and ensures that `payments` is always passed as a valid array to the client component, preventing `.map()` errors if the server action fails or returns undefined.
```
--- a/app/dashboard/banking/page.tsx
+++ b/app/dashboard/banking/page.tsx
@@ -58,16 +58,25 @@
         ? partyTypeParam
         : undefined,
-    minAmount: minAmountParam ? parseFloat(minAmountParam) : undefined,
+    minAmount: minAmountParam ? parseFloat(minAmountParam) : undefined,
   };
 
-  const result = await getApprovedPayments(filters, pagination);
+  let result;
+  try {
+    result = await getApprovedPayments(filters, pagination);
+  } catch (error) {
+    console.error("Error fetching approved payments:", error);
+    result = { payments: [], pagination: DEFAULT_PAGINATION };
+  }
+
+  const safePayments = Array.isArray(result?.payments) ? result.payments : [];
+  const safePagination = result?.pagination || DEFAULT_PAGINATION;
 
   return (
     <BankingClient
-      payments={result.payments}
-      pagination={result.pagination}
+      payments={safePayments}
+      pagination={safePagination}
       filters={filters}
     />
   );
 }
```

### `app/dashboard/banking/banking-client.tsx` (modify)
Adds optional chaining (`?.`) to nested property accesses and ensures the `payments` array defaults to an empty array. This prevents "Cannot read properties of undefined" errors during rendering if any relational data is missing from the payment object.
```
--- a/app/dashboard/banking/banking-client.tsx
+++ b/app/dashboard/banking/banking-client.tsx
@@ -150,7 +150,7 @@
 export function BankingClient({
-  payments,
+  payments = [],
   pagination,
   filters,
 }: BankingClientProps) {
@@ -300,7 +300,7 @@
-          {payments.map((payment) => (
+          {(payments || []).map((payment) => (
@@ -350,7 +350,7 @@
-            {payment.organization.name}
+            {payment.organization?.name || "N/A"}
@@ -360,7 +360,7 @@
-            {payment.case.title}
+            {payment.case?.title || "N/A"}
@@ -370,7 +370,7 @@
-            {payment.bankAccount.accountNumber}
+            {payment.bankAccount?.accountNumber || "N/A"}
```

## Test Suggestions

Framework: `Vitest with React Testing Library`

- **shouldRenderWithoutCrashingWhenPaymentsIsUndefined** *(edge case)* — Verifies that the BankingClient component handles undefined payments arrays gracefully using default parameters or optional chaining.
- **shouldRenderWithoutCrashingWhenNestedPropertiesAreMissing** *(edge case)* — Ensures that optional chaining is correctly applied to nested properties within the payment objects during rendering.
- **shouldPassEmptyArrayToClientWhenDataFetchFails** *(edge case)* — Verifies that the server component's try-catch block successfully intercepts data fetching failures and provides a safe default to the client component.
- **shouldRenderFallbackUiWhenChildThrowsError** — Tests the local Next.js Error Boundary to ensure it catches rendering exceptions and displays a user-friendly recovery UI.

## AI Confidence Scores
Plan: 85%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._