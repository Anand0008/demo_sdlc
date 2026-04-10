## IDRE-483: Add confirmation box within the admin closure (354) work flow(s)

**Jira Ticket:** [IDRE-483](https://orchidsoftware.atlassian.net//browse/IDRE-483)

## Summary
Update the administrative closure modal to use a strict 3-step confirmation sequence (Intent Verification, Financial Disclosure, Final Warning) before processing the closure, with immediate cancellation at any step.

## Implementation Plan

**Step 1: Introduce Confirmation Step State**  
Add a new state variable `confirmationStep` (e.g., `const [confirmationStep, setConfirmationStep] = useState(0)`) to track the user's progress through the new 3-step confirmation sequence. Update the modal's close/cancel handler to reset this state to 0 whenever the modal is closed, ensuring the workflow terminates completely if the user cancels.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 2: Implement Step 1: Intent Verification**  
Implement the UI for Step 1 (Intent Verification). When the user initiates the closure action, set `confirmationStep = 1`. Render a view displaying: 'You have selected the following action: "[Selected Action]". Was this your intended selection?'. Provide 'Yes' (advances to Step 2) and 'No' (closes modal and resets state) buttons.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 3: Implement Step 2: Financial Disclosure**  
Refactor the existing 'Fee Return' pop-up UI to serve as Step 2 (Financial Disclosure). When `confirmationStep === 2`, display the text: 'Completing this action will result in the following fees being returned to the parties: [Insert Fee Return Schedule here]. Would you like to proceed?'. Reuse the existing fee schedule rendering logic here. Provide 'Yes' (advances to Step 3) and 'No' (closes modal and resets state) buttons.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 4: Implement Step 3: Final Irreversibility Warning**  
Implement the UI for Step 3 (Final Irreversibility Warning). When `confirmationStep === 3`, display the text: 'This action cannot be reversed. Are you sure you want to complete this action?'. Provide 'Yes' (triggers the actual `closeCaseAdministrative` submission logic) and 'No' (closes modal and resets state) buttons.
Files: `components/admin/administrative-closure-modal.tsx`

**Risk Level:** LOW — The changes are confined to a single modal component's internal state and rendering logic. It does not alter backend closure logic or database schemas, only the user confirmation flow before the API call is made.

## Proposed Code Changes

### `components/admin/administrative-closure-modal.tsx` (modify)
This change introduces the `confirmationStep` state to track the user's progress through the new 3-step confirmation sequence. It updates the modal's close/cancel handler to reset this state to 0 whenever the modal is closed, ensuring the workflow terminates completely if the user cancels. It implements the UI for Step 1 (Intent Verification), Step 2 (Financial Disclosure), and Step 3 (Final Irreversibility Warning) as requested.
```
--- a/components/admin/administrative-closure-modal.tsx
+++ b/components/admin/administrative-closure-modal.tsx
@@ -...@@
   const [isSubmitting, setIsSubmitting] = useState(false);
+  const [confirmationStep, setConfirmationStep] = useState(0);
@@ -...@@
   const handleOpenChange = useCallback((open: boolean) => {
     if (!open) {
+      setConfirmationStep(0);
       // existing reset logic
     }
     onOpenChange(open);
   }, [onOpenChange]);
@@ -...@@
+  const handleCancelSequence = () => {
+    setConfirmationStep(0);
+    onOpenChange(false);
+  };
+
+  const advanceToStep2 = async () => {
+    // If preview data needs to be fetched from the server, ensure it is fetched here or before step 1
+    setConfirmationStep(2);
+  };
@@ -...@@
   return (
     <Dialog open={isOpen} onOpenChange={handleOpenChange}>
       <DialogContent className="sm:max-w-[600px]">
+        {confirmationStep === 1 ? (
+          <>
+            <DialogHeader>
+              <DialogTitle>Confirm Action</DialogTitle>
+            </DialogHeader>
+            <div className="py-6">
+              <p className="text-sm text-muted-foreground">
+                You have selected the following action: <strong>"{reason ? (EARLY_STAGE_OPTIONS.find(o => o.value === reason)?.label || POST_STAGE_OPTIONS.find(o => o.value === reason)?.label || reason) : ''}"</strong>. Was this your intended selection?
+              </p>
+            </div>
+            <DialogFooter>
+              <Button variant="outline" onClick={handleCancelSequence}>No</Button>
+              <Button onClick={advanceToStep2}>Yes</Button>
+            </DialogFooter>
+          </>
+        ) : confirmationStep === 2 ? (
+          <>
+            <DialogHeader>
+              <DialogTitle>Fee Return Schedule</DialogTitle>
+            </DialogHeader>
+            <div className="py-6 space-y-4">
+              <p className="text-sm text-muted-foreground">
+                Completing this action will result in the following
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Jest with React Testing Library`

- **should complete the 3-step confirmation sequence successfully** — Verifies the happy path where a user successfully navigates all three confirmation steps to complete the administrative closure.
- **should terminate the sequence and close modal when cancelled at Step 1** — Verifies that cancelling at the first step immediately terminates the workflow.
- **should terminate the sequence and close modal when cancelled at Step 2** — Verifies that cancelling at the second step (Financial Disclosure) terminates the workflow and resets progress.
- **should terminate the sequence and close modal when cancelled at Step 3** *(edge case)* — Verifies that cancelling at the final warning step terminates the workflow without submitting.
- **should display the correct action name and fee schedule dynamically based on selection** — Verifies that the modal dynamically renders the correct action name and corresponding fee schedule based on the selected closure type.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page serves as the canonical reference for the end-to-end case lifecycle, including final closure, which is directly impacted by the new administrative closure confirmation workflow.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — Provides high-level context on the IDRE case workflow phases, which will be affected by the new administrative closure rules.

**Suggested Documentation Updates:**

- IDRE Worflow: Needs to be updated to detail the new three-step confirmation sequence and cancellation logic for administrative closures.
- IDRE Case Workflow Documentation: Should be updated to reflect the new confirmation steps required before a case reaches final closure.

## AI Confidence Scores
Plan: 95%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._