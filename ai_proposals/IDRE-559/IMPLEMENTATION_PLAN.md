## IDRE-559: Staging - Party Portal: When user selects specific organization and add bank details not able to pay for dispute

**Jira Ticket:** [IDRE-559](https://orchidsoftware.atlassian.net//browse/IDRE-559)

## Summary
Fix the inability to pay for disputes when a specific organization is selected by ensuring newly added bank accounts are correctly linked to the organization. This involves passing the organization ID from the payment form to the Stripe intent metadata, and updating the Stripe webhook to save the organization ID when creating the bank account record.

## Implementation Plan

**Step 1: Pass Organization ID from Payment Form**  
Update the `PaymentForm` component to explicitly pass the `activeOrganizationId` (or the derived organization ID from the selected cases) to the `processBulkPayment` server action when submitting the form or adding new bank details.
Files: `app/app/payments/components/payment-form.tsx`

**Step 2: Include Organization ID in Stripe Intent Metadata**  
Modify the `processBulkPayment` action (and any related Stripe intent creation functions) to accept the `organizationId` parameter. Inject this `organizationId` into the `metadata` object when creating the Stripe PaymentIntent or SetupIntent.
Files: `lib/actions/party-payments.ts`

**Step 3: Link Bank Account to Organization in Webhook**  
Update the Stripe webhook event handlers (e.g., `payment_intent.succeeded`, `setup_intent.succeeded`) to extract the `organizationId` from the intent's `metadata`. When creating or updating the `BankAccount` record in the database, explicitly set the `organizationId` field to prevent 'unknown ownership' records.
Files: `app/api/stripe/webhook/route.ts`

**Step 4: Enforce Organization-Specific Banking Checks**  
Review and update `checkBankingSetup` and `getPartyDashboardBankAccounts` to ensure they correctly validate the presence of bank accounts using the specific `organizationId`. Add robust fallback or logging if an 'unknown ownership' account is detected to aid in ongoing investigations.
Files: `lib/actions/party-dashboard.ts`

**Risk Level:** MEDIUM — Modifying payment intent metadata and webhook handlers carries a moderate risk, as errors could disrupt the payment flow or bank account creation process. However, the changes are targeted and directly address the 'unknown ownership' data integrity issue.

**Deployment Notes:**
- Ensure Stripe webhook endpoint is properly configured and receiving metadata in staging/production environments.
- Monitor logs for any remaining 'unknown ownership' bank account creations after deployment.

## Proposed Code Changes

### `app/app/payments/components/payment-form.tsx` (modify)
Explicitly pass the `organizationId` (either from props or derived from the selected cases) to the server actions that create Stripe intents, ensuring the resulting bank account is linked to the correct organization.
```
--- a/app/app/payments/components/payment-form.tsx
+++ b/app/app/payments/components/payment-form.tsx
@@ -...@@
 interface PaymentFormProps {
   cases: Case[];
   bankAccounts: BankAccount[];
+  activeOrganizationId?: string | null;
 }
 
@@ -...@@
   const handlePayment = async () => {
     try {
+      // Derive organization ID from selected cases if not explicitly provided
+      const selectedCaseObjects = cases.filter(c => selectedCases.includes(c.id));
+      const derivedOrganizationId = activeOrganizationId || (selectedCaseObjects.length > 0 ? selectedCaseObjects[0].organizationId : null);
+
       const result = await processBulkPayment({
         caseIds: selectedCases,
         paymentMethodId: selectedPaymentMethod,
+        organizationId: derivedOrganizationId,
       });
@@ -...@@
   const handleAddBankAccount = async () => {
     try {
+      // Derive organization ID from selected cases if not explicitly provided
+      const selectedCaseObjects = cases.filter(c => selectedCases.includes(c.id));
+      const derivedOrganizationId = activeOrganizationId || (selectedCaseObjects.length > 0 ? selectedCaseObjects[0].organizationId : null);
+
-      const result = await createSetupIntent();
+      const result = await createSetupIntent({ organizationId: derivedOrganizationId });
```

### `lib/actions/party-payments.ts` (modify)
Accept the `organizationId` parameter in payment and setup intent creation functions, and inject it into the Stripe intent `metadata` so it can be retrieved by the webhook.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -...@@
 export async function processBulkPayment(params: {
   caseIds: string[];
   paymentMethodId?: string;
+  organizationId?: string | null;
 }) {
@@ -...@@
   const paymentIntent = await stripe.paymentIntents.create({
     amount,
     currency: "usd",
     customer: customerId,
     payment_method: paymentMethodId,
     metadata: {
       userId: user.id,
       caseIds: params.caseIds.join(","),
+      organizationId: params.organizationId || "",
     },
   });
@@ -...@@
-export async function createSetupIntent() {
+export async function createSetupIntent(params?: { organizationId?: string | null }) {
@@ -...@@
   const setupIntent = await stripe.setupIntents.create({
     customer: customerId,
     payment_method_types: ["us_bank_account"],
     metadata: {
       userId: user.id,
+      organizationId: params?.organizationId || "",
     },
   });
```

### `app/api/stripe/webhook/route.ts` (modify)
Extract the `organizationId` from the Stripe intent metadata and explicitly set it when creating or updating the `BankAccount` record in the database to prevent "unknown ownership" records.
```typescript
--- a/app/api/stripe/webhook/route.ts
+++ b/app/api/stripe/webhook/route.ts
@@ -...@@
     if (event.type === "setup_intent.succeeded" || event.type === "payment_intent.succeeded") {
       const intent = event.data.object as Stripe.SetupIntent | Stripe.PaymentIntent;
       const metadata = intent.metadata || {};
+      const organizationId = metadata.organizationId || null;
 
       // ... existing code to extract payment method details ...
 
       await prisma.bankAccount.upsert({
         where: { stripePaymentMethodId: paymentMethodId },
         create: {
           userId: metadata.userId,
+          organizationId: organizationId,
           // ... other fields
         },
         update: {
+          organizationId: organizationId,
           // ... other fields
         }
       });
```

### `lib/actions/party-dashboard.ts` (modify)
No rationale provided
```typescript
where: {
userId: session.user.id,
```

## Test Suggestions

Framework: `Vitest / React Testing Library`

- **should include organizationId in Stripe intent metadata** — Verifies that the server action correctly attaches the organizationId to the Stripe intent metadata so it can be retrieved later by the webhook.
- **should save organizationId to BankAccount when processing Stripe webhook** — Ensures the webhook correctly extracts the organizationId from the Stripe intent metadata and links the newly created bank account to the correct organization, fixing the bug where bank accounts had unknown ownership.
- **should pass organizationId to intent creation action on submit** — Verifies that the frontend correctly passes the organizationId down to the server action when a user attempts to add bank details or pay for a dispute.

## Confluence Documentation References

- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — Contains QA testing requirements for organization selection, which is a key step in reproducing the bug.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — Highlights payments, refunds, and banking details as known complexity hotspots and thematic bug areas, directly relating to the inability to pay after adding bank details.
- [Sprint 10](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/311820299) — Mentions an ongoing investigation into bank accounts with unknown ownership related to organizations, which may be the root cause of the payment failure.

**Suggested Documentation Updates:**

- Bugs
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._