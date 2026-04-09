## IDRE-611: User is not able to move case to other organization

**Jira Ticket:** [IDRE-611](https://orchidsoftware.atlassian.net//browse/IDRE-611)

## Summary
Fix frontend dialog components to correctly construct and submit the payload for moving a case to a different organization, ensuring null states are handled and update flags are accurately set.

## Implementation Plan

**Step 1: Fix organization update submission logic and handle null states**  
Update the component state initialization to safely handle cases where `currentOrganization` might be null or undefined (e.g., `useState(currentOrganization?.id || "")`). Fix the form submission handler to ensure `updateCaseOrganizationDuringReview` is called with the correct `caseId`, `partyType`, and `selectedOrganizationId`. Ensure `onSuccess` and `onClose` are properly awaited and triggered upon a successful response.
Files: `components/case-review/organization-edit-dialog.tsx`

**Step 2: Correct payload construction for organization assignments**  
Review and fix the payload construction in the submission handler. Ensure that when a user selects a new organization for either the initiating or non-initiating party, the `changed` boolean flag is accurately evaluated and set to `true` in the `OrganizationAssignmentsEditData` payload passed to the `onComplete` callback. This ensures the backend correctly identifies which party's organization needs to be updated.
Files: `components/case-review/organization-assignments-edit-modal.tsx`

**Risk Level:** LOW — The changes are confined to frontend dialog components responsible for case organization assignment. They do not alter backend database schemas or core business logic, minimizing the risk of unintended side effects.

## Proposed Code Changes

### `components/case-review/organization-edit-dialog.tsx` (modify)
Safely handle cases where `currentOrganization` is null or undefined to prevent crashes on initialization. Ensure `onSuccess` and `onClose` are properly awaited in the submit handler so the UI updates correctly after a successful API call.
```
--- components/case-review/organization-edit-dialog.tsx
+++ components/case-review/organization-edit-dialog.tsx
@@ -23,11 +23,11 @@
 interface OrganizationEditDialogProps {
   caseId: string;
   partyType: "INITIATING" | "NON_INITIATING";
-  currentOrganization: {
+  currentOrganization?: {
     id: string;
     name: string;
     type: string;
-  };
+  } | null;
   availableOrganizations: Array<{
     id: string;
     name: string;
@@ -47,14 +47,14 @@
   onSuccess,
   onOrganizationCreated
 }: OrganizationEditDialogProps) {
-  const [selectedOrganizationId, setSelectedOrganizationId] = useState(currentOrganization.id);
+  const [selectedOrganizationId, setSelectedOrganizationId] = useState(currentOrganization?.id || "");
   const [loading, setLoading] = useState(false);
   const [showCreateForm, setShowCreateForm] = useState(false);
   const [newOrgName, setNewOrgName] = useState("");
   const [creatingOrg, setCreatingOrg] = useState(false);
 
   // Update selected organization when current organization changes
   useEffect(() => {
-    setSelectedOrganizationId(currentOrganization.id);
-  }, [currentOrganization.id]);
+    setSelectedOrganizationId(currentOrganization?.id || "");
+  }, [currentOrganization?.id]);
@@ -80,15 +80,15 @@
   const handleSubmit = async (e: React.FormEvent) => {
     e.preventDefault();
     if (!selectedOrganizationId) return;
 
     setLoading(true);
     try {
       await updateCaseOrganizationDuringReview(caseId, partyType, selectedOrganizationId);
       toast.success("Organization updated successfully");
-      onSuccess();
-      onClose();
+      await onSuccess();
+      await onClose();
     } catch (error) {
       console.error("Error updating organization:", error);
       toast.error("Failed to update organization");
     } finally {
       setLoading(false);
     }
   };
```

### `components/case-review/organization-assignments-edit-modal.tsx` (modify)
Correctly evaluate the `changed` flag by comparing the original organization ID with the newly selected organization ID. This ensures the backend knows which party's organization was actually modified and processes the update accordingly.
```
--- components/case-review/organization-assignments-edit-modal.tsx
+++ components/case-review/organization-assignments-edit-modal.tsx
@@ -150,20 +150,20 @@
       await onComplete({
         caseId: initialData.caseId,
         initiatingParty: {
           id: initialData.initiatingParty.id,
           originalOrganization: {
             id: initialData.initiatingParty.organizationId,
             name: initialData.initiatingParty.organizationName,
             type: initialData.initiatingParty.organizationType,
           },
           newOrganization: selectedInitiatingOrg,
-          changed: false,
+          changed: initialData.initiatingParty.organizationId !== selectedInitiatingOrg?.id,
         },
         nonInitiatingParty: {
           id: initialData.nonInitiatingParty.id,
           originalOrganization: {
             id: initialData.nonInitiatingParty.organizationId,
             name: initialData.nonInitiatingParty.organizationName,
             type: initialData.nonInitiatingParty.organizationType,
           },
           newOrganization: selectedNonInitiatingOrg,
-          changed: false,
+          changed: initialData.nonInitiatingParty.organizationId !== selectedNonInitiatingOrg?.id,
         },
       });
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest + React Testing Library`

- **should render without crashing when currentOrganization is null** *(edge case)* — Verifies that the dialog does not crash when initialized without a current organization.
- **should await onSuccess and onClose during form submission** — Ensures that the submit handler properly awaits the success callback before closing the dialog, preventing race conditions in UI updates.
- **should correctly set the changed flag to true when a new organization is selected** — Verifies that changing the organization correctly evaluates the changed flag by comparing the new ID with the original ID.
- **should set the changed flag to false when the organization is not modified** *(edge case)* — Verifies that the changed flag remains false if the user submits the modal without actually altering the organization ID.

## Confluence Documentation References

- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — Provides an overview of the Organization Management and Admin Tools, which is the domain where users manage organizations and likely where the functionality to move cases between organizations resides.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — Contains the product requirements for the Organization Management System, which dictates the business rules and constraints for associating cases with organizations and transferring them.
- [IDRE Platform Weekly Work Summary: April 8, 2026 Updates and Enhancements](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/318275601) — Highlights that the team is currently addressing edge-case issues in the Organization Management Tool, which contextualizes this bug as part of the ongoing deployment stabilization.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: May need updating if the rules for moving cases between organizations are modified or clarified.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: Should be updated if the fix changes how administrators or users interact with the tool to move cases.

## AI Confidence Scores
Plan: 80%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._