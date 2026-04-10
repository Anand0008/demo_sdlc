## IDRE-483: Add confirmation box within the admin closure (354) work flow(s)

**Jira Ticket:** [IDRE-483](https://orchidsoftware.atlassian.net//browse/IDRE-483)

## Summary
Add a single confirmation dialog to the administrative closure workflow to prevent accidental closures, as requested by the revised requirements.

## Implementation Plan

**Step 1: Add confirmation state**  
Add a `showConfirmation` boolean state to the component to track whether the final confirmation dialog should be displayed.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 2: Intercept submission flow**  
Modify the existing form submission handler. Instead of immediately processing the administrative closure, it should set `showConfirmation` to true. Move the actual API call/submission logic into a new `handleConfirmedSubmit` function.
Files: `components/admin/administrative-closure-modal.tsx`

**Step 3: Render confirmation dialog**  
Render a standard confirmation `Dialog` when `showConfirmation` is true. The dialog should display a warning (e.g., 'This action cannot be reversed. Are you sure you want to complete this action?'). Include a 'Yes' button to trigger `handleConfirmedSubmit` and a 'Cancel' button that closes the dialog and the parent modal, returning the user to the case view as required by the ticket.
Files: `components/admin/administrative-closure-modal.tsx`

**Risk Level:** LOW — The changes are isolated to a single modal component and only add an intermediate confirmation step before executing existing logic.

## Proposed Code Changes

### `components/admin/administrative-closure-modal.tsx` (modify)
Added a `showConfirmation` state to intercept the form submission. When the user submits the administrative closure form, it now shows a final confirmation dialog warning that the action is irreversible. Clicking "Cancel" closes both the confirmation dialog and the parent modal, returning the user to the case view as requested by the ticket.
```
--- a/components/admin/administrative-closure-modal.tsx
+++ b/components/admin/administrative-closure-modal.tsx
@@ -14,6 +14,8 @@
 import { getDownloadUrlAction } from "@/lib/actions/upload";
 import { AlertCircle, CheckCircle2 } from "lucide-react";
 
+const CONFIRMATION_WARNING = "This action cannot be reversed. Are you sure you want to complete this action?";
+
 type Reason = keyof typeof CaseClosureReason;
 
 // Early Stage Options (Path 1) - When case is in INITIAL_ELIGIBILITY_REVIEW
@@ -50,6 +52,8 @@
   // ... existing state declarations ...
+  const [showConfirmation, setShowConfirmation] = useState(false);
+  const [pendingSubmitData, setPendingSubmitData] = useState<any>(null);
 
@@ -150,8 +154,15 @@
-  const onSubmit = async (data: any) => {
-    // ... existing submission logic ...
-  };
+  const onSubmit = async (data: any) => {
+    setPendingSubmitData(data);
+    setShowConfirmation(true);
+  };
+
+  const handleConfirmedSubmit = async () => {
+    if (!pendingSubmitData) return;
+    const data = pendingSubmitData;
+    // ... existing submission logic ...
+  };
 
@@ -250,7 +261,8 @@
   return (
-    <Dialog open={isOpen} onOpenChange={onOpenChange}>
+    <>
+    <Dialog open={isOpen} onOpenChange={onOpenChange}>
       <DialogContent>
         {/* ... existing modal content ... */}
       </DialogContent>
     </Dialog>
+
+    {showConfirmation && (
+      <Dialog 
+        open={showConfirmation} 
+        onOpenChange={(open) => {
+          if (!open) {
+            setShowConfirmation(false);
+            // Close parent modal as well on cancel
+            if (typeof onOpenChange === 'function') onOpenChange(false);
+            if (typeof onClose === 'function') onClose();
+          }
+        }}
+      >
+        <DialogContent>
+          <DialogHeader>
+            <DialogTitle>Final Confirmation</DialogTitle>
+          </DialogHeader>
+          <div className="py-4">
+            <p className="text-sm text-muted-foreground">{CONFIRMATIO
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Jest with React Testing Library`

- **shouldShowConfirmationDialogAndProcessClosureWhenConfirmed** — Verifies that submitting the closure form intercepts the submission, displays the irreversibility warning, and processes the closure only after final confirmation.
- **shouldCancelClosureAndCloseModalWhenCancelIsClickedOnConfirmation** *(edge case)* — Verifies that clicking 'Cancel' on the confirmation dialog terminates the sequence, does not submit the form, and closes the modal entirely as per the ticket requirements.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page is the canonical reference for the IDRE case lifecycle, including final closure. It will need to be updated to reflect the new three-step confirmation sequence for administrative closures.

**Suggested Documentation Updates:**

- IDRE Worflow: Needs to be updated to document the new three-step confirmation sequence for administrative closures, replacing the previous single "Fee Return" pop-up step.

## AI Confidence Scores
Plan: 95%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._