## IDRE-559: Staging - Party Portal: When user selects specific organization and add bank details not able to pay for dispute

**Jira Ticket:** [IDRE-559](https://orchidsoftware.atlassian.net//browse/IDRE-559)

## Summary
This plan resolves a server component rendering error on the payments page by optimizing the `getCasesForPayment` server action. The error is caused by an overly large data payload for users with many organizations. The fix involves removing unused `id` and `email` fields from the `initiatingParty` and `nonInitiatingParty` relations within the main Prisma query in `lib/actions/party-payments.ts`. This will reduce the response size and prevent the rendering failure without affecting component logic.

## Implementation Plan

**Step 1: Optimize party data fetching in `getCasesForPayment`**  
In the `getCasesForPayment` function, locate the `prisma.case.findMany` call. Within the `include` option for this call, modify the `select` clauses for the `initiatingParty` and `nonInitiatingParty` relations. Remove the `id: true` and `email: true` fields from both of these `select` clauses. These fields are currently being fetched but are not utilized by the downstream components, and their removal will decrease the data payload size. This change should be made around lines 377-392.
Files: `lib/actions/party-payments.ts`

**Risk Level:** LOW — The change is confined to a single server action and only removes unused fields from a database query. This reduces the data payload without altering any logic, making the risk of unintended side effects very low. The fix directly addresses the "huge response" issue mentioned in the ticket.

## Proposed Code Changes

### `lib/actions/party-payments.ts` (modify)
The `id` and `email` fields for the initiating and non-initiating parties were being fetched but are not used by the downstream components on the payments page. Removing them significantly reduces the size of the data payload sent to the client, which resolves the component rendering error experienced by users with access to a large number of cases and organizations. The `name` and `userId` fields, which are used, are preserved.
```typescript
--- a/lib/actions/party-payments.ts
+++ b/lib/actions/party-payments.ts
@@ -377,20 +377,16 @@
       include: {
         initiatingParty: {
           select: {
-            id: true,
             name: true,
-            email: true,
             userId: true,
           },
         },
         nonInitiatingParty: {
           select: {
-            id: true,
             name: true,
-            email: true,
             userId: true,
           },
         },
         initiatingPartyOrganization: {
           select: {
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest`

- **shouldReturnCasesWithoutUnusedPartyFields** — This test verifies that the `getCasesForPayment` function correctly removes the unused `id` and `email` fields from the party details to reduce the payload size, while retaining the fields that are required by the UI. This is the core validation for the bug fix.
- **shouldReturnEmptyArrayWhenUserHasNoCases** *(edge case)* — This test covers the edge case where a user has no cases to pay for, ensuring the function handles it gracefully without errors.

## Confluence Documentation References

- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — This weekly summary lists two tickets that are almost identical to IDRE-559: "IDRE-704: After adding new bank account, not able to pay for a dispute" and "IDRE-706: Party Portal: Toaster error when paying pending payment disputes". This indicates a recurring issue in this area of the application that a developer should be aware of.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD establishes the core business rule that a payment cannot be initiated without a verified banking account explicitly bound to an organization. It also details the data model, including the 'banking_verified' flag on the Organization table, which is central to the functionality described in the ticket.
- [Week 16](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/325582850) — This page explicitly calls out the history of a nearly identical bug, IDRE-704 ("After adding new bank account to organization not able to pay for a dispute"), noting it required "Multiple QA cycles and a reassignment before landing". This highlights that the feature is complex and has a history of difficult-to-fix bugs.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This document provides critical context about systemic issues. It identifies "Banking & Banking Dashboard Issues" and "Party Portal & User Experience" as major pain points, describing the system as "fragile," especially for users with multiple organizations. This directly relates to the ticket's description of a user selecting a specific organization and getting an error.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: The document should be updated if any business rules regarding bank account verification or organization hierarchy are modified to resolve the bug.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: A specific test case should be added to the 'Unhappy Paths' for the Payment & Party Portal section to cover this failure scenario (user with many organizations adding a new bank account) to prevent regressions.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._