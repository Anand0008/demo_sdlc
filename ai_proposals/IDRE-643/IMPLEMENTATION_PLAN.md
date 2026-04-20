## IDRE-643: Refine Organization Combine

**Jira Ticket:** [IDRE-643](https://orchidsoftware.atlassian.net//browse/IDRE-643)

## Summary
This plan refines the "Combine Organizations" feature by introducing a mandatory warning and confirmation modal before executing the merge. A new server action will be created to fetch organization details, including member emails, to check for potential primary email mismatches as required by the ticket. The frontend component will be updated to call this new action, display the warning in an `AlertDialog`, and only proceed with the merge upon explicit user confirmation, thereby preventing accidental data loss.

## Implementation Plan

**Step 1: Create Server Action to Fetch Organization Details for Merge Confirmation**  
Create a new server action `getOrganizationMergeDetails` to fetch the necessary information for the warning modal. This action will retrieve the names of the two organizations, the primary email of the target organization, and a list of all member emails from the source organization. The primary email will be sourced from the `email` field on the `Organization` model. Member emails will be retrieved by joining through the `Member` and `User` models. This action requires organization management permissions.
Files: `lib/actions/admin.ts`

**Step 2: Integrate Confirmation Dialog Trigger and Data Fetching**  
Introduce a new state to manage an `AlertDialog` for merge confirmation. The existing "Combine Organizations" form submission will be modified to call the new `getOrganizationMergeDetails` server action instead of directly performing the merge. The data returned will be used to populate and display the confirmation dialog. Add a loading state for this data-fetching step.
Files: `components/organizations-management.tsx`

**Step 3: Implement the Merge Confirmation Warning Modal UI**  
Implement the `AlertDialog` component which will display the warning message as specified in the ticket. The dialog's content will be dynamic, showing the names of the organizations being merged. It will conditionally display a warning if the target organization's primary email does not exist among the source organization's member emails. The "Confirm Merge" button in this dialog will trigger the final merge action.
Files: `components/organizations-management.tsx`

**Step 4: Handle Final Merge Confirmation and Action**  
Create a new handler function, `handleConfirmMerge`, that will be triggered by the "Confirm Merge" button in the `AlertDialog`. This function will call the existing `mergeOrganizations` server action. It will reuse the `isMerging` state to show a loading indicator on the confirmation button and will handle the success/error toast notifications and dialog closing logic upon completion.
Files: `components/organizations-management.tsx`

**Risk Level:** LOW — The changes are confined to an existing administrative feature and are primarily additive (a new server action and a confirmation modal). The core merge logic in `mergeOrganizations` is not being altered. The risk is low as the changes introduce a safety check rather than modifying the destructive action itself.

## Proposed Code Changes

### `lib/actions/admin.ts` (modify)
This new server action, `getOrganizationMergeDetails`, is required to fetch the necessary data for the confirmation modal. It retrieves the names of both organizations, the target organization's primary email, and all member emails from the source organization. This allows the frontend to perform the validation check and display the appropriate warning message as requested by the ticket.
```typescript
--- a/lib/actions/admin.ts
+++ b/lib/actions/admin.ts
@@ -1717,6 +1717,57 @@
   return 1;
 }
 
+export async function getOrganizationMergeDetails(
+  targetOrganizationId: string,
+  sourceOrganizationId: string
+) {
+  try {
+    await requireOrganizationManagementPermissions();
+
+    if (!targetOrganizationId || !sourceOrganizationId) {
+      throw new Error("Both target and source organization IDs are required.");
+    }
+
+    const [targetOrg, sourceOrg] = await Promise.all([
+      prisma.organization.findUnique({
+        where: { id: targetOrganizationId },
+        select: { id: true, name: true, email: true },
+      }),
+      prisma.organization.findUnique({
+        where: { id: sourceOrganizationId },
+        select: {
+          id: true,
+          name: true,
+          members: {
+            select: {
+              user: {
+                select: { email: true },
+              },
+            },
+          },
+        },
+      }),
+    ]);
+
+    if (!targetOrg || !sourceOrg) {
+      throw new Error("One or both organizations not found.");
+    }
+
+    const sourceMemberEmails = sourceOrg.members
+      .map((member) => member.user.email)
+      .filter((email): email is string => !!email);
+
+    return {
+      success: true,
+      data: {
+        targetOrg: { id: targetOrg.id, name: targetOrg.name, primaryEmail: targetOrg.email },
+        sourceOrg: { id: sourceOrg.id, name: sourceOrg.name, memberEmails: sourceMemberEmails },
+      },
+    };
+  } catch (error: any) {
+    console.error("Get organization merge details error:", error);
+    return { success: false, error: error.message || "Failed to fetch organization details for merge." };
+  }
+}
+
 export async function mergeOrganizations(
   primaryOrganizationId: string,
   secondaryOrganizationId: string
```

### `components/organizations-management.tsx` (modify)
These changes update the organization management component to support the new merge confirmation flow.
1.  **State and Imports**: New state variables (`mergeConfirmOpen`, `mergeDetails`, `isFetchingMergeDetails`) are added to manage the confirmation modal and its data. `AlertDialog` components and the `AlertTriangle` icon are imported.
2.  **Event Handlers**: The original `handleMergeOrganizations` is replaced by two new functions:
    *   `handleInitiateMerge`: Triggered by the form, it calls the new `getOrganizationMergeDetails` action and opens the confirmation modal with the fetched data.
    *   `handleConfirmMerge`: Triggered by the confirmation modal, it executes the actual `mergeOrganizations` action and handles the final UI updates.
3.  **UI**: An `AlertDialog` is added to display the confirmation message and the conditional warning about email mismatches. The "Combine" button in the initial form is updated to show a "Checking..." state while fetching details. This provides a safer, more informative user experience, preventing accidental merges.
```
--- a/components/organizations-management.tsx
+++ b/components/organizations-management.tsx
@@ -17,6 +17,16 @@
   DialogTitle,
   DialogTrigger,
 } from "@/components/ui/dialog";
+import {
+  AlertDialog,
+  AlertDialogAction,
+  AlertDialogCancel,
+  AlertDialogContent,
+  AlertDialogDescription,
+  AlertDialogFooter,
+  AlertDialogHeader,
+  AlertDialogTitle,
+} from "@/components/ui/alert-dialog";
 import {
   Table,
   TableBody,
@@ -50,6 +60,7 @@
   ChevronsUpDown,
   Check,
   Network,
+  AlertTriangle,
 } from "lucide-react";
 import {
   createOrganization,
@@ -57,6 +68,7 @@
   listOrganizations,
   updateOrganizationDetails,
   mergeOrganizations,
+  getOrganizationMergeDetails,
 } from "@/lib/actions/admin";
 import { ManageMembersDialog } from "./organizations/manage-members-dialog";
 import {
@@ -122,6 +134,19 @@
   otherOrganizations: Array<{ id: string; name: string }>;
 }
 
+interface MergeDetails {
+  targetOrg: {
+    id: string;
+    name: string;
+    primaryEmail: string | null;
+  };
+  sourceOrg: {
+    id: string;
+    name: string;
+    memberEmails: string[];
+  };
+}
+
 const FILTER_DEFINITIONS = [
   {
     value: "financial-enabled",
@@ -361,6 +386,10 @@
   const [isMerging, setIsMerging] = useState(false);
   const [mergeError, setMergeError] = useState<string | null>(null);
 
+  const [mergeConfirmOpen, setMergeConfirmOpen] = useState(false);
+  const [mergeDetails, setMergeDetails] = useState<MergeDetails | null>(null);
+  const [isFetchingMergeDetails, setIsFetchingMergeDetails] = useState(false);
+
 
   const [searchTerm, setSearchTerm] = useState("");
   const [activeFilters, setActiveFilters] = useState<string[]>([]);
@@ -463,6 +492,19 @@
     });
   }, [organizations, searchTerm, activeFilters]);
 
+  const emailMismatch = useMemo(() => {
+    if (!mergeDetails) return false;
+    const { targetOrg, sourceOrg } = mergeDetails;
+    // Only show warning if target org has a primary email and it's not found among source members
+    
... (truncated — see full diff in files)
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Vitest`

- **shouldReturnCorrectMergeDetailsForValidOrganizations** — Verifies that the server action correctly fetches and returns the required data for the merge confirmation modal when given valid inputs.
- **shouldThrowErrorIfOrganizationNotFound** *(edge case)* — Ensures the server action handles cases where one or both of the specified organizations do not exist.
- **shouldDisplayWarningModalWhenPrimaryEmailsDoNotMatch** — Tests the primary feature requirement: a warning modal is shown when a potential email mismatch is detected between the two organizations.
- **shouldDisplayStandardConfirmationWhenEmailsMatch** — Verifies that the special warning is omitted when there is no email mismatch, providing a standard confirmation flow.
- **shouldCallMergeOrganizationsActionOnConfirm** — Ensures that the final merge action is triggered correctly when the user confirms the operation in the modal.
- **shouldNotCallMergeActionAndCloseModalOnCancel** — Tests the cancellation flow, ensuring that no merge action is performed if the user cancels.
- **shouldHandleErrorWhenFetchingMergeDetailsFails** *(edge case)* — Verifies that the UI gracefully handles server errors when fetching pre-merge details, providing clear feedback to the user.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This Product Requirements Document (PRD) is the foundational document for the entire Organization Management feature, of which this ticket is a part. It details the core problem of duplicate organizations, the target two-level data model (Parent/Sub-Organization), the four key actor types, and the original deduplication strategy. It provides the essential business context and technical constraints for the developer.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a user-focused overview of the existing "Duplicate Organization Detection" and "Combine Organizations" tools. It is relevant because it shows the current implementation and UI that the developer is tasked with refining, including the detection logic (name similarity, domain match) and the entry points for the combine action.
- [Proposed Changes to Address Current Issues](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/246906881) — This page contains high-level meeting notes that explicitly call out the need to "Add intelligent suggestions to easily identify duplicate organizations" for the "Organization Merge Tool". Crucially, it also identifies a key operational constraint: merging is currently blocked by invoice-related bugs, a critical piece of information for the developer implementing the merge logic.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD outlines the plan for organization management. It should be updated to reflect the specific logic and UI/UX implemented for the refined merge/combine functionality.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This document serves as a user guide for the admin tools. It will need to be updated with new screenshots and descriptions of the refined "Combine Organizations" workflow, including the new warning modal.

## AI Confidence Scores
Plan: 100%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._