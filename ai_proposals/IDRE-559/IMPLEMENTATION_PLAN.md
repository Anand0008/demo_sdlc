## IDRE-559: Staging - Party Portal: When user selects specific organization and add bank details not able to pay for dispute

**Jira Ticket:** [IDRE-559](https://orchidsoftware.atlassian.net//browse/IDRE-559)

## Summary
This plan addresses a UI rendering error on the payments page that occurs when submitting an ACH payment with a large number of cases. The fix involves modifying the `processBulkPayment` server action in `lib/party-actions.ts` to return a minimal success message instead of a large data payload. The client component, `app/app/payments/components/payment-form.tsx`, will be updated to handle this new response by showing a success toast and then triggering a server-side data refresh, which resolves the rendering issue.

## Implementation Plan

**Step 1: Modify `processBulkPayment` Server Action to Return Minimal Response**  
Locate the `processBulkPayment` server action. Modify the function's return statement to prevent it from sending a large payload (like the full list of updated cases) back to the client. Instead, upon successful processing, it should return a minimal, serializable object containing only a success flag and perhaps a batch identifier. For example: `return { success: true, data: { message: "Payment processing started." } };`
Files: `lib/party-actions.ts`

**Step 2: Update Payment Form to Handle New Action Response and Refresh**  
In the form submission handler that calls `processBulkPayment`, update the logic that processes the returned result. Instead of expecting a large data object to update the component's state, the logic should now handle the new minimal success object. On success, display a toast notification to the user and then call `router.refresh()` to reload the page's data from the server. This ensures the UI reflects the new payment status without causing a rendering error from a large data payload. The `useRouter` hook is already imported in this component.
Files: `app/app/payments/components/payment-form.tsx`

**Risk Level:** LOW — The issue is confined to the staging environment and a specific user flow. The proposed change is minimal, targeting only the data transfer between a server action and a client component, and uses a standard pattern (action followed by router refresh) to resolve the issue, which has a low risk of side effects.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
The `processBulkPayment` server action was re-fetching all cases and returning them to the client. This large data payload was causing the client-side component to crash. This change removes the unnecessary data fetching and returns a simple success message, which is much smaller and avoids the rendering issue. The client will be responsible for refreshing its data.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -249,30 +249,12 @@
     // The client will handle UI updates via router.refresh().
   }
 
-  // Re-fetch cases to update the UI
-  const { data: partyUser } = await getPartyUserFromSession();
-  if (!partyUser) {
-    return { success: false, error: "User not found." };
-  }
-
-  const updatedCasesResult = await getCasesForPayment({
-    partyUserId: partyUser.id,
-    organizationId: activeOrganizationId,
-    page: 1,
-    pageSize: 20, // Default page size
-    partyType: partyType || undefined,
-  });
-
-  if (!updatedCasesResult.success) {
-    return {
-      success: false,
-      error: "Could not retrieve updated cases after payment.",
-    };
-  }
-
   return {
     success: true,
-    data: {
-      cases: updatedCasesResult.data.cases,
-      totalCases: updatedCasesResult.data.totalCases,
-      totalPages: updatedCasesResult.data.totalPages,
-    },
+    data: {
+      message:
+        "Payment processing has been initiated. The list will update shortly.",
+    },
   };
 }
```

### `app/app/payments/components/payment-form.tsx` (modify)
This change updates the form submission handler to correctly process the new, minimal response from the `processBulkPayment` action. Instead of attempting to update local state with a large data payload (which is no longer sent), it now displays a success toast and calls `router.refresh()`. This triggers a fresh data fetch from the server, updating the UI safely and efficiently without causing the rendering crash.
```
--- a/app/app/payments/components/payment-form.tsx
+++ b/app/app/payments/components/payment-form.tsx
@@ -581,18 +581,17 @@
     setIsSubmitting(false);
 
     if (result.success) {
-      toast.success("Payment successful!");
-      // Update local state with the new data from the server action
-      setCases(result.data.cases);
-      setTotalCases(result.data.totalCases);
-      setPagination(prev => ({
-        ...prev,
-        totalPages: result.data.totalPages,
-        currentPage: 1,
-      }));
+      toast.success(
+        result.data.message ||
+          "Payment processing initiated. The page will now refresh."
+      );
+
+      // Instead of updating local state with a large payload,
+      // trigger a server-side refresh of the page data.
+      // This avoids the component rendering error from the large response.
+      router.refresh();
+
       // Reset form state after submission
       form.reset({ ...values, selectedCases: [] });
       setSelectedRows({});
       setSelectAll(false);
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldShowSuccessToastAndRefreshOnSuccessfulPayment** — Verifies the new success flow where the component handles a minimal success response, shows a toast, and triggers a client-side refresh instead of processing a large data payload.
- **shouldShowErrorToastWhenPaymentFails** *(edge case)* — Ensures that if the server action fails, the user is shown an error message and the page does not attempt to refresh, allowing the user to try again.
- **shouldDisableSubmitButtonWhileProcessingPayment** — Verifies the UI provides feedback to the user and prevents duplicate submissions while the payment is being processed.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — The ticket describes a bug that occurs when a user selects a specific organization to add bank details for payment. This PRD outlines the business rules and expected functionality for the Organization Management System, providing essential context for how this feature should work.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document identifies that the payments, refunds, and banking modules are known "complexity hotspots" and a common source of bugs. This is critical operational context for a developer fixing a payment-related issue, as it highlights the need for careful implementation and thorough regression testing.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This document should be reviewed after the fix is implemented to ensure it accurately reflects any changes to the component's behavior, especially if new constraints or handling for large data responses are introduced.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: This document should be updated to include a specific test case for payment flows involving organizations with a large number of associated entities to prevent future performance regressions.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._