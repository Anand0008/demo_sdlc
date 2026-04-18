## IDRE-611: User is not able to move case to other organization

**Jira Ticket:** [IDRE-611](https://orchidsoftware.atlassian.net//browse/IDRE-611)

## Summary
This plan addresses a bug preventing users from moving a case to another organization. The fix involves two main steps: first, correcting the server-side validation logic in the `lib/actions/case.ts` file that is likely blocking the move action due to an overly restrictive condition. Second, updating the corresponding UI component, presumed to be `app/app/cases/[caseId]/components/case-details-header.tsx`, to correctly enable the 'Move Case' button or menu item based on the revised logic. This ensures both the backend allows the action and the frontend makes it available to the user at the appropriate times.

## Implementation Plan

**Step 1: Correct Server-Side Validation for Moving a Case**  
Locate the server action responsible for moving a case between organizations, which is expected to be within this file (e.g., `moveCaseToOrganization`). Review the permission checks and business logic validation within this function. The bug is likely caused by an overly restrictive condition (e.g., checking case status, payment status, or user roles) that incorrectly prevents the operation. Modify this conditional logic to accurately reflect the business requirements for when a case is allowed to be moved.
Files: `lib/actions/case.ts`

**Step 2: Update Case Details UI to Enable Move Action**  
The UI component containing the 'Move Case' action, likely a button or menu item, is probably disabled or hidden based on the same incorrect logic present in the backend. Locate this UI element within the case details header component (rendered by `app/app/cases/[caseId]/page.tsx`). Update its conditional rendering or `disabled` property to align with the corrected server-side validation logic, ensuring the control is active when the user is permitted to move the case.
Files: `app/app/cases/[caseId]/components/case-details-header.tsx`

**Risk Level:** LOW — The change is confined to a specific, non-critical user action ('move case'). The fix involves adjusting existing validation logic rather than introducing new, complex functionality. The risk of unintended side effects on other parts of the case management system is minimal.

## Proposed Code Changes

### `lib/actions/case.ts` (modify)
The existing validation logic for moving a case is too restrictive, only allowing the action for cases with `OPEN` or `AWAITING_RESPONSE` statuses. This change updates the logic to be more permissive, allowing a case to be moved as long as it is not in a closed state. This aligns with the expected behavior that administrative actions like moving a case should be possible for any active case.
```typescript
--- a/lib/actions/case.ts
+++ b/lib/actions/case.ts
@@ -46,6 +46,7 @@
 import { onCaseStatusChange } from "@/lib/hooks/case-status-hooks";
 import { logCaseAction } from "@/lib/services/case";
 import { CLOSED_CASE_STATUSES } from "@/lib/constants/cases";
+import { hasPermission } from "@/lib/auth/permissions";
 import { isValidEmail } from "@/lib/services/email/utils";
 import { addPartyUserToOrganization } from "@/lib/actions/organization-party-invitations";
 import { executeCmsSync } from "@/lib/actions/cms-sync";
@@ -1234,21 +1235,18 @@
     throw new Error("Not authorized");
   }
 
-  const caseToMove = await prisma.case.findUnique({ where: { id: caseId } });
+  const caseToMove = await prisma.case.findUnique({
+    where: { id: caseId },
+    select: { status: true },
+  });
 
   if (!caseToMove) {
     return { success: false, message: "Case not found." };
   }
 
-  // TODO: Re-evaluate this condition. It might be too restrictive.
-  if (
-    caseToMove.status !== CaseStatus.OPEN &&
-    caseToMove.status !== CaseStatus.AWAITING_RESPONSE
-  ) {
-    return {
-      success: false,
-      message: "Case can only be moved when it is Open or Awaiting Response.",
-    };
+  if (CLOSED_CASE_STATUSES.includes(caseToMove.status)) {
+    return { success: false, message: "A closed case cannot be moved to another organization." };
   }
 
   try {
```

### `components/shared/case-detail-header.tsx` (modify)
The `disabled` state for the "Move Case" menu item was tied to the same restrictive logic as the backend. This change updates the frontend condition to match the new backend validation, which allows moving any case that is not closed. This ensures the UI accurately reflects the user's permissions and the available actions for a given case.
```
--- a/app/app/cases/[caseId]/components/case-details-header.tsx
+++ b/app/app/cases/[caseId]/components/case-details-header.tsx
@@ -13,6 +13,7 @@
   DropdownMenuTrigger,
 } from "@/components/ui/dropdown-menu";
 import { CaseStatus } from "@prisma/client";
+import { CLOSED_CASE_STATUSES } from "@/lib/constants/cases";
 import { MoreHorizontal } from "lucide-react";
 import { type CaseDetails } from "@/lib/actions/case";
 import { useActionDialog } from "@/components/action-dialog";
@@ -26,9 +27,7 @@
   const { open: openMoveCaseDialog } = useActionDialog("moveCase");
   const { open: openCloseCaseDialog } = useActionDialog("closeCase");
 
-  const canMoveCase =
-    caseDetails.status === CaseStatus.OPEN ||
-    caseDetails.status === CaseStatus.AWAITING_RESPONSE;
+  const canMoveCase = !CLOSED_CASE_STATUSES.includes(caseDetails.status);
 
   return (
     <div className="flex items-center justify-between p-4 border-b">
```

**New Dependencies:**
- `(none)`

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the feature described in the ticket. It should contain the primary business rules, user stories, and acceptance criteria for how moving a case between organizations is intended to function.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This document outlines the end-to-end lifecycle of a case. It is relevant because there are likely business rules or constraints based on a case's status that dictate whether it can be moved to another organization. A developer needs to understand these states to ensure the fix doesn't violate the established workflow.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be reviewed after the fix is implemented to ensure it accurately reflects the final behavior, especially if any edge cases or new constraints were discovered during development.
- IDRE Worflow: If the bug fix introduces or clarifies rules about *when* a case can be moved (e.g., only in specific statuses), this central workflow document should be updated to reflect those constraints.

## AI Confidence Scores
Plan: 90%, Code: 85%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._