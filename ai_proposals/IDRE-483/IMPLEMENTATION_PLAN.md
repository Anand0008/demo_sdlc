## IDRE-483: Add confirmation box within the admin closure (354) work flow(s)

**Jira Ticket:** [IDRE-483](https://orchidsoftware.atlassian.net//browse/IDRE-483)

## Summary
This plan introduces a three-step confirmation sequence into the `AdministrativeClosureModal` to prevent accidental case closures. I will add a state management system to the modal to navigate between three views: 1) Intent Verification, 2) Financial Disclosure (the existing modal view), and 3) a Final Irreversibility Warning. The final submission action will only be callable from the third step, ensuring a deliberate and confirmed user action. This change is isolated to the frontend and reuses existing patterns, posing a low risk.

## Implementation Plan

**Step 1: Add Step Management State**  
Introduce a new state variable `step` to manage the three-step confirmation flow within the `AdministrativeClosureModal` component. The state will track whether the user is on step 1 (intent verification), step 2 (financial preview), or step 3 (final confirmation). Also, update the `useEffect` hook that resets the modal's state to also reset the step to 1 when the modal is closed.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 2: Implement Step 1: Intent Verification UI**  
Conditionally render the content of the `DialogContent` based on the `step` state. For `step === 1`, display the intent verification message, "You have selected the following action: '{action}'. Was this your intended selection?". Use the `formatEnumValue` or `formatClosureReason` function from `lib/utils/enum-helpers.ts` to get the display-friendly name of the selected `reason`. The footer for this step will contain a "Cancel" button and a "Yes - Continue" button which will set the step to 2.
Files: `components/admin/administrative-closure-modal.tsx`, `lib/utils/enum-helpers.ts`

**Step 3: Adapt Existing UI for Step 2: Financial Disclosure**  
For `step === 2`, render the existing modal content which includes the reason selector, notes textarea, file upload, and financial preview. The primary button in the `DialogFooter` will be changed to "Yes - Proceed". Its `onClick` handler will validate that the 'notes' field is not empty and then advance the state to `step = 3`.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 4: Implement Step 3: Final Irreversibility Warning UI**  
For `step === 3`, render the final confirmation UI. This will include a `DialogHeader` with "Final Confirmation" and a `DialogDescription` with the warning "This action cannot be reversed. Are you sure you want to complete this action?". The `DialogFooter` will have a "Cancel" button and a final confirmation button, "Yes - Complete Action", which will trigger the original submission logic by calling either `handleMarkPending` or `handleFinalize`.
Files: `components/admin/administrative-closure-modal.tsx`

**Risk Level:** LOW — The changes are confined to the client-side UI of a single modal. The backend actions are not being modified, only the user flow leading to their invocation. An existing component (`case-closure-action-modal.tsx`) already implements this exact 3-step pattern, providing a clear and tested implementation to follow.

## Proposed Code Changes

### `components/admin/administrative-closure-modal.tsx` (modify)
This change implements the three-step confirmation workflow within the `AdministrativeClosureModal`.
- A new state variable `step` is introduced to manage the current stage of the confirmation process.
- The modal's content and footer are now rendered conditionally based on the `step`.
- **Step 1 (Intent Verification):** The user selects a reason, and a confirmation message appears. A "Yes - Continue" button moves them to the next step.
- **Step 2 (Financial Disclosure):** The user fills in the required notes, views the financial preview, and clicks "Yes - Proceed" to continue.
- **Step 3 (Final Warning):** A final, irreversible action warning is displayed. The "Yes - Complete Action" button triggers the original submission logic.
- This new flow is only applied when initiating a new administrative closure, not when finalizing a pending one, preserving existing functionality for cases already in that state.
- The `DialogDescription` component and `formatClosureReason` helper are imported to support the new UI elements.
```
--- a/components/admin/administrative-closure-modal.tsx
+++ b/components/admin/administrative-closure-modal.tsx
@@ -1,6 +1,6 @@
 "use client";
 
 import { useEffect, useMemo, useState, useCallback } from "react";
-import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
+import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
 import { Button } from "@/components/ui/button";
 import { Label } from "@/components/ui/label";
 import { Textarea } from "@/components/ui/textarea";
@@ -12,6 +12,7 @@
 import { getAdministrativeClosurePendingDraft } from "@/lib/actions/administrative-closure-draft";
 import { getDownloadUrlAction } from "@/lib/actions/upload";
 import { AlertCircle, CheckCircle2 } from "lucide-react";
+import { formatClosureReason } from "@/lib/utils/enum-helpers";
 
 type Reason = keyof typeof CaseClosureReason;
 
@@ -62,6 +63,7 @@
 }
 
 export function AdministrativeClosureModal({ open, onOpenChange, caseId, currentStatus, userRole, onSuccess }: AdministrativeClosureModalProps) {
+  const [step, setStep] = useState(1);
   const [reason, setReason] = useState<Reason | "">("");
   const [notes, setNotes] = useState("");
   const [documentKey, setDocumentKey] = useState<string | undefined>();
@@ -83,6 +85,9 @@
   // Check if we're in pending administrative closure mode (finalizing step)
   const isPendingAdminClosure = currentStatus === "PENDING_ADMINISTRATIVE_CLOSURE";
 
+  // Determine if we are in the new multi-step closure flow
+  const isNewClosureFlow = !isPendingAdminClosure && currentStatus !== "PENDING_CLOSURE_PAYMENTS";
+
   // Determine if payments are complete (both parties paid)
   const paymentsComplete = paymentStatus.initiatingPartyPaid && paymentStatus.nonInitiatingPartyPaid;
 
@@ -156,6 +161,7 @@
       setDocumentKey(undefined);
       setPreview(null);
       setPaymentStatus({ initiatingPartyPaid: false, nonInitiatingPartyPa
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Jest`

- **shouldNavigateThroughAllThreeStepsAndSubmitOnFinalConfirmation** — Tests the full three-step confirmation happy path for a new administrative closure.
- **shouldCancelTheWorkflowAtStep1** — Ensures the user can cancel the workflow at the first step.
- **shouldCancelTheWorkflowAtStep2** — Ensures the user can cancel the workflow at the second step.
- **shouldCancelTheWorkflowAtStep3** — Ensures the user can cancel the workflow at the final step.
- **shouldDisableProceedButtonOnStep2WhenFormIsInvalid** *(edge case)* — Verifies that form validation is still enforced on the financial disclosure step before proceeding.
- **shouldNotShowThreeStepFlowWhenFinalizingAPendingClosure** — This is a regression test to ensure the existing workflow for finalizing a pending closure is not affected by the new three-step confirmation flow.

## Confluence Documentation References

- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — This page provides the specific status codes (`PENDING_ADMINISTRATIVE_CLOSURE`, `CLOSED_ADMINISTRATIVE`) and reason codes (`SETTLEMENT`, `WITHDRAWAL_IP`, etc.) for the administrative closure workflows mentioned in the ticket. It also details the fee and refund rules, which are essential for the second step of the confirmation modal (Financial Disclosure).
- [Proposed Changes to Address Current Issues](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/246906881) — This document confirms that the ticket is part of a larger initiative (JMS-354) to create structured, guided paths for administrative closures. This context is important as it highlights the business driver: preventing staff from making mistakes, particularly around refunds and payments when closing cases.
- [Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/296910852) — This page lists the end-to-end testing requirements for administrative closures (Ineligible, Withdrawn, Settled). The developer needs to be aware that the new three-step confirmation flow will be subject to this QA process and that test cases will need to be updated.

**Suggested Documentation Updates:**

- IDRE Case Workflow Documentation: The new three-step confirmation modal is a significant change to the administrative closure process and should be explicitly documented in the 'Administrative Closure Path' section.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: The E2E test plan for admin closures should be updated to incorporate testing the new three-step confirmation sequence.

## AI Confidence Scores
Plan: 100%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._