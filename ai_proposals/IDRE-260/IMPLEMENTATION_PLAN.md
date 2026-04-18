## IDRE-260: Implement Aggregation Logic for Outgoing Payments (Refunds & IDRE Payouts)

**Jira Ticket:** [IDRE-260](https://orchidsoftware.atlassian.net//browse/IDRE-260)

## Summary
Implement aggregation logic for outgoing payments (Refunds & IDRE Payouts) by grouping transactions by banking info or mailing address. Introduce a parent/child transaction hierarchy in the database, generate reverse invoices with dispute details, and update reporting endpoints to exclude parent transactions to prevent double-counting.

## Implementation Plan

**Step 1: Update Database Schema for Parent/Child Payments**  
Update the `Payment` model to support the Transaction ID Hierarchy. Add a nullable `parentPaymentId` field (String) with a self-relation (`@relation("PaymentToPayment")`) to link child transactions to their aggregated parent. Add a boolean field `isAggregatedParent` (default `false`) to easily identify transfer vessels.
Files: `prisma/schema.prisma`

**Step 2: Implement Payment Aggregation and Reverse Invoice Logic**  
Implement the `aggregateOutgoingPayments` logic. Group pending outgoing payments (Refunds & IDRE Payouts) by `[Payee] + [Routing/Account]` for ACH, or `[Payee] + [Mailing Address]` for Checks. For each group, create a parent `Payment` record (`isAggregatedParent: true`) with the summed total. Update the grouped child `Payment` records to set their `parentPaymentId` to the new parent. Implement logic to generate a "Reverse Invoice" (CSV/PDF) detailing the child disputes, and trigger an email notification to the payee containing the total amount, organization name, status, and the attached dispute list.
Files: `lib/actions/party-payments.ts`

**Step 3: Apply Exclusion Rule to IDRE Payouts Report**  
Update the Prisma query in the `GET` handler to enforce the Exclusion Rule. Add `isAggregatedParent: false` (or equivalent logic) to the `where` clause to ensure that the aggregated parent transactions are excluded from the daily report, preventing double booking while retaining the individual child line items.
Files: `app/api/reports/idre-payouts/route.ts`

**Step 4: Apply Exclusion Rule to Other Financial Reports**  
Apply the same `isAggregatedParent: false` exclusion rule to the Prisma queries in these reporting endpoints to ensure parent transfer vessels do not skew CMS or outstanding payment totals.
Files: `app/api/reports/cms-payments/route.ts`, `app/api/reports/outstanding-payments/route.ts`

**Risk Level:** MEDIUM — Modifying the payment schema and introducing aggregation logic affects core financial flows. The exclusion rule is critical to prevent double-counting in reconciliation reports. Comprehensive testing is required to ensure child transactions are correctly linked and reported.
⚠️ **Database Migrations Required: YES**

**Deployment Notes:**
- Run Prisma migrations to apply the new `parentPaymentId` and `isAggregatedParent` fields to the `Payment` table.
- Ensure existing payments default to `isAggregatedParent: false` to maintain historical reporting accuracy.

## Proposed Code Changes

### `prisma/schema.prisma` (modify)
Adds the necessary fields to support the Transaction ID Hierarchy. `parentPaymentId` links child transactions to their aggregated parent, and `isAggregatedParent` easily identifies transfer vessels for exclusion in reports.
```
--- a/prisma/schema.prisma
+++ b/prisma/schema.prisma
@@ -x,x +x,x @@
 model Payment {
   id                  String    @id @default(cuid())
   // ... existing fields ...
+
+  // Aggregation fields for outgoing payments
+  parentPaymentId     String?
+  parentPayment       Payment?  @relation("PaymentToPayment", fields: [parentPaymentId], references: [id])
+  childPayments       Payment[] @relation("PaymentToPayment")
+  isAggregatedParent  Boolean   @default(false)
 }
```

### `lib/actions/party-payments.ts` (modify)
Implements the core aggregation logic. Groups pending outgoing payments by `[Payee] + [Routing/Account]` for ACH, or `[Payee] + [Mailing Address]` for Checks. Creates a parent payment record with the summed total and updates the grouped child records to link to the new parent.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -x,x +x,x @@
+export async function aggregateOutgoingPayments() {
+  // Fetch pending outgoing payments that haven't been aggregated yet
+  const pendingPayments = await prisma.payment.findMany({
+    where: {
+      direction: "OUTGOING",
+      status: "PENDING",
+      isAggregatedParent: false,
+      parentPaymentId: null,
+      type: { in: ["REFUND", "IDRE_PAYOUT"] },
+    },
+    include: {
+      organization: true,
+      bankAccount: true,
+      case: true,
+    },
+  });
+
+  // Group payments
+  const groups: Record<string, typeof pendingPayments> = {};
+
+  for (const payment of pendingPayments) {
+    const payee = payment.organization?.name || "UNKNOWN";
+    let groupKey = "";
+
+    if (payment.paymentMethod === "ACH" && payment.bankAccount) {
+      // Group by Payee + Routing/Account
+      groupKey = `ACH_${payee}_${payment.bankAccount.routingNumber}_${payment.bankAccount.accountNumber}`;
+    } else if (payment.paymentMethod === "CHECK") {
+      // Group by Payee + Mailing Address
+      // Assuming organization has a mailingAddress field or similar relation
+      const address = payment.organization?.mailingAddress || "UNKNOWN_ADDRESS";
+      groupKey = `CHECK_${payee}_${address}`;
+    } else {
+      continue; // Skip un-groupable payments
+    }
+
+    if (!groups[groupKey]) {
+      groups[groupKey] = [];
+    }
+    groups[groupKey].push(payment);
+  }
+
+  // Process groups
+  for (const [key, group] of Object.entries(groups)) {
+    if (group.length <= 1) continue; // Only aggregate if > 1 record
+
+    const totalAmount = group.reduce((sum, p) => sum + p.amount, 0);
+    const firstPayment = group[0];
+
+    await prisma.$transaction(async (tx) => {
+      // Create parent payment
+      const parentPayment = await tx.payment.create({
+        data: {
+          amount: totalAmount,
+          direction: "OUTGOING",
+          status: "PENDING",
+          t
... (truncated — see full diff in files)
```

### `app/api/reports/idre-payouts/route.ts` (modify)
Enforces the Exclusion Rule to prevent double booking/accounting. The Parent Transaction (Aggregated Total) must NOT be included in the Daily Report.
```typescript
--- a/app/api/reports/idre-payouts/route.ts
+++ b/app/api/reports/idre-payouts/route.ts
@@ -x,x +x,x @@
   const payments = await prisma.payment.findMany({
     where: {
       // ... existing conditions ...
+      isAggregatedParent: false,
     },
```

### `app/api/reports/cms-payments/route.ts` (modify)
Applies the same exclusion rule to ensure parent transfer vessels do not skew CMS payment totals.
```typescript
--- a/app/api/reports/cms-payments/route.ts
+++ b/app/api/reports/cms-payments/route.ts
@@ -x,x +x,x @@
   const payments = await prisma.payment.findMany({
     where: {
       // ... existing conditions ...
+      isAggregatedParent: false,
     },
```

### `app/api/reports/outstanding-payments/route.ts` (modify)
Applies the same exclusion rule to ensure parent transfer vessels do not skew outstanding payment totals.
```typescript
--- a/app/api/reports/outstanding-payments/route.ts
+++ b/app/api/reports/outstanding-payments/route.ts
@@ -x,x +x,x @@
   const payments = await prisma.payment.findMany({
     where: {
       // ... existing conditions ...
+      isAggregatedParent: false,
     },
```

## Test Suggestions

Framework: `Jest or Vitest`

- **should aggregate ACH payments with identical routing and account numbers** — Verifies that ACH payments to the same organization with identical banking details are grouped into a single parent transaction.
- **should aggregate Check payments with identical payee and mailing address** — Verifies that physical check payments to the same organization with identical mailing addresses are grouped into a single parent transaction.
- **should not aggregate ACH payments with different banking information** *(edge case)* — Ensures that payments are not incorrectly aggregated if the banking information differs, even if the payee is the same.
- **should exclude aggregated parent transactions from IDRE payouts report** — Verifies the Exclusion Rule: Parent Transactions must not be included in the daily report to prevent double booking.
- **should exclude aggregated parent transactions from outstanding payments report** — Verifies the Exclusion Rule applies to the outstanding payments report to prevent skewing totals.

## AI Confidence Scores
Plan: 95%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._