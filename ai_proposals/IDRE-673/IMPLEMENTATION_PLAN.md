## IDRE-673: Track and report on why individual disputes are found ineligible

**Jira Ticket:** [IDRE-673](https://orchidsoftware.atlassian.net//browse/IDRE-673)

## Summary
This plan introduces ineligible sub-statuses to provide more detail on why a dispute is ineligible. It involves updating the `CaseStatus` enum in the database, modifying the administrative closure modal to capture the specific ineligibility reason, updating the corresponding server action to save this new status, and finally, adding the new sub-statuses to the filtering options on the main cases page and its backing search API.

## Implementation Plan

**Step 1: Update Database Schema and Create Migration**  
In the `prisma/schema.prisma` file, extend the `CaseStatus` enum to include the new ineligible sub-statuses. The new values should be formatted like `Ineligible_Cooling_Off_Period_Not_Completed`. After updating the schema, run `npx prisma migrate dev --name add_ineligible_substatuses` to generate a new migration file that will apply these changes to the database. The list of reasons is provided in the ticket description. Example values to add: `Ineligible_Eligible_For_State_Process`, `Ineligible_Exceeded_Four_Day_Timeline`, `Ineligible_Incorrectly_Batched`, etc. for all 13 reasons.
Files: `prisma/schema.prisma`

**Step 2: Add Sub-Status Selector to Administrative Closure Modal**  
Modify the `AdministrativeClosureModal` component. When a user selects a closure reason that corresponds to 'Ineligible' (e.g., `EARLY_INELIGIBLE`), conditionally render a new, required `Select` dropdown. This dropdown will be populated with the ineligible sub-statuses. The selected sub-status value must be stored in the component's state and passed to the `closeCaseAdministrative` server action upon submission.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 3: Update Server Action to Save Sub-Status**  
Update the relevant server action, likely `closeCaseAdministrative`, within this file. Modify its signature to accept the new ineligible sub-status as an argument. In the `prisma.case.update` call within this function, set the `status` field to the new sub-status value received from the modal, instead of the generic `INELIGIBLE` status.
Files: `lib/actions/administrative-closure.ts`

**Step 4: Add New Sub-Statuses to Case Filter UI**  
In the `CasesPageClient` component, update the status filter dropdown. Add the new ineligible sub-statuses as options in the `<Select>` component that controls the `statusFilter` state. This will allow users to filter the case list by each specific ineligibility reason.
Files: `app/app/cases/components/cases-page-client.tsx`

**Step 5: Update Case Search API to Handle New Statuses**  
Modify the `GET` handler in the case search API. The code that builds the Prisma query currently uses `searchParams.get("status")`. Ensure that the query logic correctly handles the new `Ineligible_*` status values passed from the frontend filter. No major changes are expected if the query is already dynamically using the status parameter in the `where` clause, but this must be verified.
Files: `app/api/cases/search/route.ts`

**Risk Level:** MEDIUM — The ticket involves modifying the `CaseStatus` enum, which is a core part of the application's state machine. The Confluence documentation explicitly calls out that status transitions related to case closure are a 'complexity hotspot' and a frequent source of bugs, particularly concerning payments and refunds. While the changes are straightforward, the risk of unintended side effects in financial logic is medium.
⚠️ **Database Migrations Required: YES**

**Deployment Notes:**
- As per the Confluence documentation, changes to case closure statuses are a 'complexity hotspot'. Thorough regression testing is required to ensure this change does not negatively impact payment and refund logic.
- After deployment, existing cases with the 'INELIGIBLE' status will remain as they are. There is no requirement to backfill a sub-status for them.

## Proposed Code Changes

### `prisma/schema.prisma` (modify)
This change extends the `CaseStatus` enum in the database schema to include the new, specific sub-statuses for ineligible cases as required by the ticket. This is the foundational change that allows the system to store the new granular statuses.
```
--- a/prisma/schema.prisma
+++ b/prisma/schema.prisma
@@ -100,6 +100,20 @@
   FINAL_DETERMINATION_PENDING
   FINAL_DETERMINATION_RENDERED
   INELIGIBLE
+  Ineligible_Cooling_Off_Period_Not_Completed
+  Ineligible_Eligible_For_State_Process
+  Ineligible_Exceeded_Four_Day_Timeline
+  Ineligible_Incorrectly_Batched
+  Ineligible_Incorrectly_Bundled
+  Ineligible_Item_Or_Service_Not_Covered_By_Plan
+  Ineligible_Item_Or_Service_Not_NSA_Eligible
+  Ineligible_Notice_Of_Initiation_Not_Submitted
+  Ineligible_Open_Negotiation_Not_Complete
+  Ineligible_Open_Negotiation_Not_Initiated
+  Ineligible_Other
+  Ineligible_Plan_Not_Subject_To_NSA
+  Ineligible_Prior_To_Applicable_Policy_Year
   INELIGIBLE_PENDING_ADMIN_FEE
   CLOSED_DEFAULT
   CLOSED_DEFAULT_IP
```

### `components/admin/administrative-closure-modal.tsx` (modify)
This change updates the administrative closure modal to conditionally display a required dropdown for selecting an ineligibility reason when a user chooses to mark a case as "Ineligible". It introduces state to manage the selected sub-status and passes this value to the `closeCaseAdministrative` server action upon submission, ensuring the specific reason is captured.
```
--- a/components/admin/administrative-closure-modal.tsx
+++ b/components/admin/administrative-closure-modal.tsx
@@ -13,6 +13,22 @@
 import { getAdministrativeClosurePendingDraft } from "@/lib/actions/administrative-closure-draft";
 import { getDownloadUrlAction } from "@/lib/actions/upload";
 import { AlertCircle, CheckCircle2 } from "lucide-react";
+import { CaseStatus } from "@prisma/client";
+
+const INELIGIBLE_SUBSTATUS_OPTIONS = [
+  { value: CaseStatus.Ineligible_Cooling_Off_Period_Not_Completed, label: 'Cooling off period not completed' },
+  { value: CaseStatus.Ineligible_Eligible_For_State_Process, label: 'Eligible for state process' },
+  { value: CaseStatus.Ineligible_Exceeded_Four_Day_Timeline, label: 'Exceeded four-day timeline' },
+  { value: CaseStatus.Ineligible_Incorrectly_Batched, label: 'Incorrectly batched' },
+  { value: CaseStatus.Ineligible_Incorrectly_Bundled, label: 'Incorrectly bundled' },
+  { value: CaseStatus.Ineligible_Item_Or_Service_Not_Covered_By_Plan, label: 'Item or service not covered by plan' },
+  { value: CaseStatus.Ineligible_Item_Or_Service_Not_NSA_Eligible, label: 'Item or service not NSA-eligible' },
+  { value: CaseStatus.Ineligible_Notice_Of_Initiation_Not_Submitted, label: 'Notice of initiation not submitted' },
+  { value: CaseStatus.Ineligible_Open_Negotiation_Not_Complete, label: 'Open negotiation not complete' },
+  { value: CaseStatus.Ineligible_Open_Negotiation_Not_Initiated, label: 'Open negotiation not initiated' },
+  { value: CaseStatus.Ineligible_Other, label: 'Other' },
+  { value: CaseStatus.Ineligible_Plan_Not_Subject_To_NSA, label: 'Plan not subject to NSA' },
+  { value: CaseStatus.Ineligible_Prior_To_Applicable_Policy_Year, label: 'Prior to applicable policy year' },
+].sort((a, b) => a.label.localeCompare(b.label));
 
 type Reason = keyof typeof CaseClosureReason;
 
@@ -51,6 +67,7 @@
   const [reason, setReason] = useState<Reason | ''>('');
   const [notes, setNotes] = useState('');
   const [files, set
... (truncated — see full diff in files)
```

### `lib/actions/administrative-closure.ts` (modify)
This change modifies the `closeCaseAdministrative` server action to accept and process the new `ineligibleSubStatus`. It adds validation to ensure a valid sub-status is provided when a case is closed as `EARLY_INELIGIBLE` and uses this sub-status to update the case record in the database, replacing the generic `INELIGIBLE` status.
```typescript
--- a/lib/actions/administrative-closure.ts
+++ b/lib/actions/administrative-closure.ts
@@ -1,5 +1,5 @@
 'use server';
-import { CaseStatus } from '@prisma/client';
+import { CaseStatus } from '@prisma/client'; // Keep existing import
 import { revalidatePath } from 'next/cache';
 import { z } from 'zod';
 import { prisma } from '@/lib/prisma';
@@ -21,6 +21,7 @@
   reason: z.nativeEnum(CaseClosureReason),
   notes: z.string().optional(),
   files: z.array(z.object({ key: z.string(), name: z.string() })).optional(),
+  ineligibleSubStatus: z.nativeEnum(CaseStatus).optional(),
 });
 
 export async function closeCaseAdministrative(
@@ -52,8 +53,12 @@
   let newStatus: CaseStatus;
 
   switch (reason) {
-    case CaseClosureReason.EARLY_INELIGIBLE:
-      newStatus = CaseStatus.INELIGIBLE;
+    case CaseClosureReason.EARLY_INELIGIBLE: {
+      if (!ineligibleSubStatus || !Object.values(CaseStatus).includes(ineligibleSubStatus)) {
+        return { success: false, message: 'A valid ineligibility reason must be provided.' };
+      }
+      newStatus = ineligibleSubStatus;
       break;
+    }
     case CaseClosureReason.DISMISSAL:
       newStatus = CaseStatus.NOTICE_OF_DISMISSAL_NON_PAYMENT;
       break;
```

### `app/app/cases/components/cases-page-client.tsx` (modify)
This change adds the new ineligible sub-statuses to the status filter dropdown on the main cases page. This allows users to filter the case list by each specific ineligibility reason, fulfilling a core requirement of the ticket.
```
--- a/app/app/cases/components/cases-page-client.tsx
+++ b/app/app/cases/components/cases-page-client.tsx
@@ -31,6 +31,20 @@
   { value: 'FINAL_DETERMINATION_PENDING', label: 'Final Determination Pending' },
   { value: 'FINAL_DETERMINATION_RENDERED', label: 'Final Determination Rendered' },
   { value: 'INELIGIBLE', label: 'Ineligible' },
+  { value: 'Ineligible_Cooling_Off_Period_Not_Completed', label: 'Ineligible – Cooling off period not completed' },
+  { value: 'Ineligible_Eligible_For_State_Process', label: 'Ineligible – Eligible for state process' },
+  { value: 'Ineligible_Exceeded_Four_Day_Timeline', label: 'Ineligible – Exceeded four-day timeline' },
+  { value: 'Ineligible_Incorrectly_Batched', label: 'Ineligible – Incorrectly batched' },
+  { value: 'Ineligible_Incorrectly_Bundled', label: 'Ineligible – Incorrectly bundled' },
+  { value: 'Ineligible_Item_Or_Service_Not_Covered_By_Plan', label: 'Ineligible – Item or service not covered by plan' },
+  { value: 'Ineligible_Item_Or_Service_Not_NSA_Eligible', label: 'Ineligible – Item or service not NSA-eligible' },
+  { value: 'Ineligible_Notice_Of_Initiation_Not_Submitted', label: 'Ineligible – Notice of initiation not submitted' },
+  { value: 'Ineligible_Open_Negotiation_Not_Complete', label: 'Ineligible – Open negotiation not complete' },
+  { value: 'Ineligible_Open_Negotiation_Not_Initiated', label: 'Ineligible – Open negotiation not initiated' },
+  { value: 'Ineligible_Other', label: 'Ineligible – Other' },
+  { value: 'Ineligible_Plan_Not_Subject_To_NSA', label: 'Ineligible – Plan not subject to NSA' },
+  { value: 'Ineligible_Prior_To_Applicable_Policy_Year', label: 'Ineligible – Prior to applicable policy year' },
   { value: 'INELIGIBLE_PENDING_ADMIN_FEE', label: 'Ineligible Pending Admin Fee' },
   { value: 'CLOSED_DEFAULT', label: 'Closed - Default' },
   { value: 'CLOSED_DEFAULT_IP', label: 'Closed - Default IP' },
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Vitest`

- **shouldRenderSubStatusSelectWhenIneligibleIsChosen** — Verifies that the sub-status dropdown is conditionally rendered only when the "Ineligible" status is selected.
- **shouldShowValidationErrorIfIneligibleButNoSubStatusIsSelected** *(edge case)* — Ensures the sub-status is required when a case is being closed as ineligible.
- **shouldCallServerActionWithCorrectSubStatusOnSubmit** — Verifies the happy path where the form is submitted correctly with the selected ineligible sub-status.
- **shouldUpdateCaseWithIneligibleSubStatusWhenProvided** — Tests the happy path for the server action, ensuring it correctly updates the case with the new specific sub-status.
- **shouldThrowErrorWhenClosingAsIneligibleWithoutSubStatus** *(edge case)* — Tests the error handling path where a case is marked ineligible without specifying the required reason.
- **shouldSuccessfullyCloseCaseWithNonIneligibleStatus** — This is a regression test to ensure that existing administrative closure reasons continue to function as expected without being affected by the new sub-status logic.
- **shouldDisplayNewIneligibleSubStatusesInFilterDropdown** — Verifies that the new ineligible sub-statuses are available as filtering options on the main cases page UI.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the end-to-end case lifecycle and statuses. The ticket proposes changing one of these core statuses ('Ineligible'), making this document essential for understanding the current state and the impact of the change.
- [Bugs](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/285736962) — This page identifies that case status transitions related to closure types, including 'Ineligible', are a 'major complexity hotspot' and a source of high-impact bugs. This is a critical operational constraint for a developer to consider when modifying the 'Ineligible' status.

**Suggested Documentation Updates:**

- IDRE Worflow: This page is the canonical reference for the case lifecycle. It needs to be updated to include the new 'Ineligible' sub-statuses and the requirement to select one when closing a case as ineligible.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._