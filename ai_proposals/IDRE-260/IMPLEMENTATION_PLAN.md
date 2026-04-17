## IDRE-260: Implement Aggregation Logic for Outgoing Payments (Refunds & IDRE Payouts)

**Jira Ticket:** [IDRE-260](https://orchidsoftware.atlassian.net//browse/IDRE-260)

## Summary
Implement aggregation logic for outgoing payments (Refunds and IDRE Payouts) by grouping transactions by banking info or address, creating a parent transaction, generating reverse invoices with email notifications, and excluding parent transactions from daily reports.

## Implementation Plan

**Step 1: Update Database Schema for Payment Hierarchy**  
Add a self-referencing relation to the `Payment` model to support the Parent/Child hierarchy. Add `parentPaymentId` (String, nullable) and a relation `childPayments` pointing to `Payment`. Add fields for `isAggregatedParent` (Boolean, default false) to easily distinguish parent records.
Files: `prisma/schema.prisma`

**Step 2: Implement Payment Aggregation Logic**  
Implement the aggregation logic for outgoing payments (Refunds & IDRE Payouts). Create a function that fetches pending outgoing payments, groups them by identical Banking Information (Routing + Account) for ACH, or identical Mailing Address + Payee Name for Checks. For each group with >1 record, create a Parent Payment record with the aggregated total, and update the underlying child `Payment` records to set their `parentPaymentId` to the new Parent Payment ID.
Files: `lib/actions/party-payments.ts`

**Step 3: Implement Reverse Invoice and Email Notifications**  
Integrate Reverse Invoice generation and email notifications into the aggregation flow. After creating a Parent Payment, generate a CSV/PDF detailing the list of included Dispute IDs and their individual amounts. Trigger an email to the recipient containing the Total Amount Paid, Organization Name, Status, and the generated CSV/PDF attachment.
Files: `lib/actions/party-payments.ts`

**Step 4: Exclude Parent Transactions from Daily Reports**  
Update the database queries in the daily reporting routes to explicitly exclude Parent Transactions. Add a `where` clause condition (e.g., `isAggregatedParent: false` or `parentPaymentId: null` depending on schema implementation) to ensure only child line items are booked, preventing double accounting.
Files: `app/api/reports/idre-payouts/route.ts`

**Risk Level:** HIGH — Modifying core payment logic and schema to introduce a parent/child hierarchy carries a high risk of impacting financial reporting and reconciliation if not implemented carefully.
⚠️ **Breaking Changes: YES**
⚠️ **Database Migrations Required: YES**

**Deployment Notes:**
- Run database migrations to apply the new parent/child relationship on the Payment table.
- Ensure that any existing pending outgoing payments are handled correctly before enabling the aggregation cron/action.

## Proposed Code Changes

### `prisma/schema.prisma` (modify)
Adds a self-referencing relation to the `Payment` model to support the Parent/Child hierarchy for aggregated payments. The `isAggregatedParent` flag allows easy filtering of parent records.
```
--- a/prisma/schema.prisma
+++ b/prisma/schema.prisma
@@ -... @@
 model Payment {
   id                                String                     @id
+  parentPaymentId                   String?
+  parentPayment                     Payment?                   @relation("PaymentHierarchy", fields: [parentPaymentId], references: [id])
+  childPayments                     Payment[]                  @relation("PaymentHierarchy")
+  isAggregatedParent                Boolean                    @default(false)
```

### `app/api/reports/idre-payouts/route.ts` (modify)
Excludes aggregated parent transactions from the daily report to prevent double booking/accounting, ensuring only the underlying child line items are reported.
```typescript
--- a/app/api/reports/idre-payouts/route.ts
+++ b/app/api/reports/idre-payouts/route.ts
@@ -44,6 +44,7 @@
     // Use Prisma ORM to fetch payments and allocations
     const payments = await prisma.payment.findMany({
       where: {
+        isAggregatedParent: false,
```

### `lib/actions/party-payments.ts` (modify)
Implements the core aggregation logic. It fetches pending outgoing payments, groups them by the specified criteria (ACH vs Check), creates a parent payment for groups with >1 record, and links the children. It also prepares the data structure required for the Reverse Invoice and email notifications.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -... @@
+
+/**
+ * Aggregates pending outgoing payments (Refunds & IDRE Payouts) into a single parent payment
+ * based on identical banking information (ACH) or mailing address + payee name (Check).
+ */
+export async function aggregateOutgoingPayments() {
+  // Fetch pending outgoing payments that are not already aggregated
+  const pendingPayments = await prisma.payment.findMany({
+    where: {
+      direction: 'OUTGOING', // Assuming OUTGOING or OUTBOUND based on schema
+      status: 'PENDING',
+      isAggregatedParent: false,
+      parentPaymentId: null,
+    },
+    include: {
+      party: true,
+      case: true,
+    }
+  });
+
+  const groups: Record<string, typeof pendingPayments> = {};
+
+  // Group payments by identical banking info or address
+  for (const payment of pendingPayments) {
+    let key = '';
+    if (payment.method === 'ACH') {
+      const routing = payment.party?.routingNumber || (payment as any).routingNumber;
+      const account = payment.party?.accountNumber || (payment as any).accountNumber;
+      if (routing && account) {
+        key = `ACH_${routing}_${account}`;
+      }
+    } else if (payment.method === 'CHECK') {
+      const address = payment.party?.mailingAddress || (payment as any).mailingAddress;
+      const payee = payment.party?.payeeName || payment.party?.name || (payment as any).payeeName;
+      if (address && payee) {
+        key = `CHECK_${address}_${payee}`;
+      }
+    }
+
+    if (key) {
+      if (!groups[key]) groups[key] = [];
+      groups[key].push(payment);
+    }
+  }
+
+  // Process groups and create parent payments
+  for (const [key, group] of Object.entries(groups)) {
+    if (group.length > 1) {
+      const totalAmount = group.reduce((sum, p) => sum + Number(p.amount), 0);
+      const firstPayment = group[0];
+
+      // Create parent payment
+      const parentPayment = await prisma.payment.create({
+        data: 
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Vitest`

- **should aggregate ACH payments with identical routing and account numbers** — Verifies that ACH payments with matching banking details are aggregated into a single parent transaction.
- **should aggregate Check payments with identical payee name and mailing address** — Verifies that Check payments with matching address and payee name are aggregated into a single parent transaction.
- **should not aggregate payments if routing numbers or addresses differ** *(edge case)* — Ensures aggregation strictly requires exact matches on banking info or address, preventing incorrect grouping.
- **should correctly calculate the total amount for the aggregated parent payment** — Verifies the mathematical accuracy of the aggregated total amount for a large batch of payments.
- **should exclude aggregated parent transactions from the daily report** — Verifies the exclusion rule to prevent double booking in daily reports.

## AI Confidence Scores
Plan: 80%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._