## IDRE-706: Party Portal: When trying to pay for a dispute with pending payment getting some toaster error

**Jira Ticket:** [IDRE-706](https://orchidsoftware.atlassian.net//browse/IDRE-706)

## Summary
Improve error handling when a user attempts to pay for a dispute that already has a pending payment by catching the payment lock conflict and returning a user-friendly error message to the frontend toaster.

## Implementation Plan

**Step 1: Handle pending payment conflict in Stripe payment action**  
In `createStripePaymentIntent`, update the `catch` block to specifically check for errors thrown by `assertNoConflictingCasePartyPaymentSource` (or check the error message for conflict keywords). Return a user-friendly error message such as 'One or more selected disputes already have a pending payment. Please check your pending payments.' instead of a generic or raw error string.
Files: `lib/actions/stripe-payment.ts`

**Step 2: Handle pending payment conflict in bulk payment action**  
In `processBulkPayment` (and any other relevant payment processing actions in this file), implement the same error handling for payment locks. Catch the conflict error and return a structured `ActionResult` with a user-friendly error message indicating that a pending payment already exists.
Files: `lib/actions/party-payments.ts`

**Step 3: Display user-friendly error in payment form toaster**  
Review the form submission handlers that call `createStripePaymentIntent` and `processBulkPayment`. Ensure that if the action returns `success: false` with an `error` message, the exact user-friendly error message is passed to `toast.error()`. Optionally, if a conflict error is detected, trigger a refresh of the case list to remove the already-pending cases from the selectable list.
Files: `app/app/payments/components/payment-form.tsx`

**Risk Level:** LOW — The changes are isolated to error handling and user messaging during the payment initiation phase. No core payment processing logic or database schemas are altered.

## Proposed Code Changes

### `lib/actions/stripe-payment.ts` (modify)
Catch payment lock conflict errors and return a user-friendly message instead of a raw error string.
```typescript
--- a/lib/actions/stripe-payment.ts
+++ b/lib/actions/stripe-payment.ts
@@ -150,6 +150,17 @@
     };
   } catch (error) {
     console.error("Error creating Stripe payment intent:", error);
+
+    const errorMessage = error instanceof Error ? error.message : String(error);
+    if (
+      errorMessage.includes("pending payment") ||
+      errorMessage.includes("conflict") ||
+      errorMessage.includes("already has a payment") ||
+      errorMessage.includes("Payment lock")
+    ) {
+      return {
+        success: false,
+        error: "One or more selected disputes already have a pending payment. Please check your pending payments.",
+      };
+    }
+
     return {
       success: false,
       error: error instanceof Error ? error.message : "Failed to create payment intent",
```

### `lib/actions/party-payments.ts` (modify)
Catch payment lock conflict errors in bulk payments and return a user-friendly message.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -200,6 +200,17 @@
     };
   } catch (error) {
     console.error("Error processing bulk payment:", error);
+
+    const errorMessage = error instanceof Error ? error.message : String(error);
+    if (
+      errorMessage.includes("pending payment") ||
+      errorMessage.includes("conflict") ||
+      errorMessage.includes("already has a payment") ||
+      errorMessage.includes("Payment lock")
+    ) {
+      return {
+        success: false,
+        error: "One or more selected disputes already have a pending payment. Please check your pending payments.",
+      };
+    }
+
     return {
       success: false,
       error: error instanceof Error ? error.message : "Failed to process bulk payment",
```

### `app/app/payments/components/payment-form.tsx` (modify)
Ensure the user-friendly error message is displayed in the toaster, and refresh the page if a pending payment conflict is detected so the user's case list is updated.
```
--- a/app/app/payments/components/payment-form.tsx
+++ b/app/app/payments/components/payment-form.tsx
@@ -250,7 +250,11 @@
       }
 
       if (!result.success) {
-        toast.error(result.error || "Failed to process payment");
+        toast.error(result.error || "Failed to process payment");
+        if (result.error?.includes("pending payment")) {
+          // Refresh the page after a short delay to update the list of available cases
+          setTimeout(() => window.location.reload(), 2500);
+        }
         return;
       }
```

## Test Suggestions

Framework: `Vitest`

- **shouldReturnUserFriendlyErrorWhenPaymentLockConflictOccurs** *(edge case)* — Verifies that a payment lock conflict in the Stripe payment action is caught and transformed into a user-friendly error message.
- **shouldReturnUserFriendlyErrorForBulkPaymentLockConflict** *(edge case)* — Verifies that a payment lock conflict in the party payments action is caught and transformed into a user-friendly error message.
- **shouldDisplayToasterErrorAndRefreshPageOnPendingPaymentConflict** *(edge case)* — Verifies that the PaymentForm component displays the correct toaster error and refreshes the page when a pending payment conflict is returned from the server action.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._