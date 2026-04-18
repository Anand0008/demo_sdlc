## IDRE-643: Refine Organization Combine

**Jira Ticket:** [IDRE-643](https://orchidsoftware.atlassian.net//browse/IDRE-643)

## Summary
This plan outlines the creation of a feature to merge two organizations. The implementation includes a new server action in `lib/actions/organization.ts` to handle the database updates within a transaction, a new warning modal component as specified in the ticket to ensure user awareness of the irreversible action, and UI modifications to the company management page (`app/dashboard/company/page.tsx`) to trigger the process. A final verification step ensures that financial reporting, particularly the case ledger, remains accurate after a merge.

## Implementation Plan

**Step 1: Create `mergeOrganizations` Server Action**  
Create a new server action `mergeOrganizations(sourceOrgId: string, targetOrgId:string)`. This action must use a Prisma transaction (`prisma.$transaction`) to atomically perform the following: 1. Identify all models with a foreign key to the `Organization` model by inspecting `prisma/schema.prisma`. This includes, but is not limited to, `CaseParty`, `Invoice`, `Payment`, `User`, and `BankAccount`. 2. Update all records in these related tables, changing their `organizationId` from `sourceOrgId` to `targetOrgId`. 3. After all related records are successfully re-associated, delete the source organization record (`prisma.organization.delete`). 4. Ensure the action is protected and can only be executed by users with appropriate administrative roles.
Files: `lib/actions/organization.ts`, `prisma/schema.prisma`

**Step 2: Create Merge Organization Warning Modal**  
Create a new file and component for the warning modal. This component will accept the source and target organization objects as props. It will display the specific warning text from the ticket description. The component will be responsible for comparing the organizations' primary emails/domains and conditionally rendering the "Security & Data Mismatch" warning. The 'Confirm Merge' button within the modal will invoke the `mergeOrganizations` server action. To prevent accidental execution, the confirm button should be disabled until the user types a confirmation word (e.g., "MERGE") into a text field.
Files: `components/company/merge-organization-warning-modal.tsx`

**Step 3: Add Merge UI to Company Management Page**  
Modify the company management page to allow an administrator to select two organizations to be merged. This will likely involve adding checkboxes to the list of organizations and a 'Merge Selected' button. When clicked, this button will open the `MergeOrganizationWarningModal` and pass the data for the two selected organizations.
Files: `app/dashboard/company/page.tsx`

**Step 4: Verify Case Ledger and Financial Reporting Logic**  
This is a verification step. After the merge functionality is implemented, thoroughly test that financial views and reports function correctly. Specifically, review the logic in `getCaseLedgerObligation` and related functions to ensure that billing history and ledger data from the merged organization are correctly attributed to the target organization. No code changes are expected here unless testing reveals aggregation issues.
Files: `lib/payments/case-ledger.ts`

**Risk Level:** HIGH — The action of merging organizations is destructive and irreversible. It involves complex database updates across multiple tables (users, cases, billing, payments). An error in the transaction could lead to data corruption, orphaned records, or incorrect financial reporting. The risk is heightened by the lack of explicit acceptance criteria for handling data conflicts between the merging entities.

**Deployment Notes:**
- This is a high-risk, irreversible action. It should be deployed behind a feature flag and initially tested in a staging environment with production data copies.
- An announcement should be made to internal admin users about the new functionality, with clear instructions on its use and associated risks.

## Proposed Code Changes

### `lib/actions/organization.ts` (modify)
This change adds two new server actions. `getAllOrganizationsForAdmin` provides the data needed for the new merge UI. `mergeOrganizations` is the core of the feature, performing the database updates within a transaction to ensure data integrity. It reassigns all related entities from the source organization to the target before deleting the source, and is protected by admin role checks.
```typescript
--- a/lib/actions/organization.ts
+++ b/lib/actions/organization.ts
@@ -1,9 +1,12 @@
 "use server";
 
+import { revalidatePath } from "next/cache";
+import { z } from "zod";
 import { auth } from "@/lib/auth/server";
 import { headers } from "next/headers";
 import { prisma } from "@/lib/database";
 import { OrganizationType } from "@prisma/client";
+import { hasRequiredRole } from "../auth/permissions";
 
 type ActionResult<T = unknown> = {
   success: boolean;
@@ -73,3 +76,112 @@
     return { success: false, error: "Failed to search organizations" };
   }
 }
+
+/**
+ * Get all organizations for admin selection UI.
+ * Not paginated. Use with caution.
+ */
+export async function getAllOrganizationsForAdmin(): Promise<
+  ActionResult<Array<{ id: string; name: string; email: string | null }>>
+> {
+  try {
+    const session = await auth.api.getSession({ headers: await headers() });
+    if (!session) return { success: false, error: "Authentication required" };
+
+    if (!hasRequiredRole(session.user.role, ["master-admin", "capitol-bridge-admin"])) {
+      return { success: false, error: "Unauthorized" };
+    }
+
+    const organizations = await prisma.organization.findMany({
+      select: { id: true, name: true, email: true },
+      orderBy: { name: "asc" },
+    });
+    return { success: true, data: organizations };
+  } catch (error) {
+    console.error("Error fetching all organizations:", error);
+    return { success: false, error: "Failed to fetch organizations" };
+  }
+}
+
+const MergeOrganizationsSchema = z.object({
+  sourceOrgId: z.string().cuid(),
+  targetOrgId: z.string().cuid(),
+});
+
+export async function mergeOrganizations(
+  sourceOrgId: string,
+  targetOrgId: string
+): Promise<ActionResult<{ success: boolean }>> {
+  try {
+    const session = await auth.api.getSession({ headers: await headers() });
+    if (!session) {
+      return { success: false, error: "Authentication required" };
+    }
+
+    if (!hasRequiredRole(session.user.
... (truncated — see full diff in files)
```

### `app/dashboard/company/page.tsx` (modify)
This change modifies the main company management page to support the new merge feature. It fetches the list of all organizations and passes them to the new `MergeControls` client component, which will handle the user interaction for selecting and merging organizations. The existing `CompanyPageClient` is preserved and rendered below the new merge UI.
```
--- a/app/dashboard/company/page.tsx
+++ b/app/dashboard/company/page.tsx
@@ -4,6 +4,7 @@
 import { listAdminInvitations } from "@/lib/actions/admin-invitations";
 import { listPartyInvitations } from "@/lib/actions/party-invitations";
 import { getPartyUsersWithOrganizations } from "@/lib/actions/party-users";
+import { getAllOrganizationsForAdmin } from "@/lib/actions/organization";
 import {
   serializeAdminInvitation,
   serializePartyInvitation,
@@ -14,6 +15,7 @@
   PartyInvitationSummary,
 } from "@/lib/types/invitations";
 import type { PartyUserWithOrganizations } from "@/lib/actions/party-users";
 import CompanyPageClient from "./company-page-client";
+import MergeControls from "./merge-controls";
 
 export default async function CompanyPage() {
   const session = await getCurrentSession();
@@ -29,10 +31,11 @@
     redirect("/dashboard");
   }
 
-  const [adminInvitationsResult, partyInvitationsResult, partyUsersResult] = await Promise.all([
+  const [adminInvitationsResult, partyInvitationsResult, partyUsersResult, organizationsResult] = await Promise.all([
     listAdminInvitations(),
     listPartyInvitations(),
     getPartyUsersWithOrganizations(),
+    getAllOrganizationsForAdmin(),
   ]);
 
   const adminInvitations: AdminInvitationSummary[] =
@@ -62,4 +65,22 @@
         .filter(Boolean)
         .join(" - ") || "Unable to load party invitations";
 
+  const organizations = organizationsResult.success ? organizationsResult.data : [];
+  // TODO: Handle organizationsError, maybe show an alert to the user
+
   return (
+    <div className="space-y-8">
+      <MergeControls organizations={organizations || []} />
+      <CompanyPageClient
+        adminInvitations={adminInvitations}
+        partyInvitations={partyInvitations}
+        partyUsers={
+          partyUsersResult.success ? partyUsersResult.data.partyUsers : []
+        }
+        adminInvitationsError={adminInvitationsError}
+        partyInvitationsError={partyInvitationsError}
+      />
+
... (truncated — see full diff in files)
```

### `app/dashboard/company/merge-controls.tsx` (create)
This new client component provides the UI for selecting the source and target organizations for the merge operation. It maintains the state for user selections and controls the visibility of the confirmation modal. Creating this as a separate component allows us to keep the main page (`page.tsx`) as a Server Component while encapsulating interactive, client-side logic here.
```
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { MergeOrganizationWarningModal } from "@/components/company/merge-organization-warning-modal";

type OrganizationData = {
  id: string;
  name: string;
  email: string | null;
};

interface MergeControlsProps {
  organizations: OrganizationData[];
}

export default function MergeControls({ organizations }: MergeControlsProps) {
  const router = useRouter();
  const [sourceOrgId, setSourceOrgId] = useState<string | null>(null);
  const [targetOrgId, setTargetOrgId] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const sourceOrg = organizations.find(o => o.id === sourceOrgId) || null;
  const targetOrg = organizations.find(o => o.id === targetOrgId) || null;

  const handleMergeSuccess = () => {
    setSourceOrgId(null);
    setTargetOrgId(null);
    // Refresh the page to show updated organization list
    router.refresh();
  };

  const canMerge = sourceOrgId && targetOrgId && sourceOrgId !== targetOrgId;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Merge Organizations</CardTitle>
          <CardDescription>
            Select two organizations to merge. All data from the source organization will be moved to the target organization, and the source organization will be deleted. This action is irreversible.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 sm:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor="source-org">Source Organization (to be merged and deleted)</Label>
            <Select value={sourceOrgId ?? ""} onValueCha
... (truncated — see full diff in files)
```

### `components/company/merge-organization-warning-modal.tsx` (create)
This new modal component fulfills a key requirement from the ticket. It presents a clear warning to the user about the consequences of merging organizations, including a specific alert for email mismatches. To prevent accidental confirmation, it requires the user to type "MERGE" before enabling the final confirmation button, which then invokes the `mergeOrganizations` server action.
```
"use client";

import { useState } from "react";
import { toast } from "react-hot-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { mergeOrganizations } from "@/lib/actions/organization";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Terminal } from "lucide-react";

interface OrganizationData {
  id: string;
  name: string;
  email?: string | null;
}

interface MergeOrganizationWarningModalProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  sourceOrg: OrganizationData | null;
  targetOrg: OrganizationData | null;
  onMergeSuccess: () => void;
}

const CONFIRMATION_TEXT = "MERGE";

export function MergeOrganizationWarningModal({
  isOpen,
  onOpenChange,
  sourceOrg,
  targetOrg,
  onMergeSuccess,
}: MergeOrganizationWarningModalProps) {
  const [confirmationInput, setConfirmationInput] = useState("");
  const [isMerging, setIsMerging] = useState(false);

  if (!sourceOrg || !targetOrg) {
    return null;
  }

  const handleMerge = async () => {
    setIsMerging(true);
    const toastId = toast.loading("Merging organizations...");

    try {
      const result = await mergeOrganizations(sourceOrg.id, targetOrg.id);

      if (result.success) {
        toast.success("Organizations merged successfully.", { id: toastId });
        onMergeSuccess();
        onOpenChange(false);
        setConfirmationInput("");
      } else {
        toast.error(result.error || "Failed to merge organizations.", { id: toastId });
      }
    } catch (error) {
      toast.error("An unexpected error occurred.", { id: toastId });
      console.error("Merge failed:", error);
    } finally {
      setIsMerging(false);
    }
  };

  const emailsMatch = sourceOrg.em
... (truncated — see full diff in files)
```

**New Dependencies:**
- ``zod` (already a dependency, used for schema validation in the new server action)`
- ``react-hot-toast` (assumed to be an existing dependency for user feedback)`

## Test Suggestions

Framework: `Jest`

- **shouldSuccessfullyMergeTwoOrganizations** — Verifies the happy path for the mergeOrganizations server action, ensuring all database operations within the transaction complete successfully for an admin user.
- **shouldThrowErrorIfUserIsNotAdmin** — Ensures that only users with the 'admin' role can perform the merge operation.
- **shouldThrowErrorIfSourceAndTargetAreTheSame** *(edge case)* — Validates that the function prevents a user from selecting the same organization as both the source and the destination for a merge.
- **shouldRollbackTransactionOnDatabaseError** *(edge case)* — Verifies that if any step in the database transaction fails, the entire operation is aborted and an error is handled gracefully.
- **shouldDisplayEmailMismatchWarningWhenEmailsDiffer** — Tests that the modal correctly displays a warning when the primary emails of the two organizations do not match, as per the ticket's requirements.
- **shouldEnableConfirmButtonWhenUserTypesMerge** — Ensures the safety check requiring the user to type 'MERGE' correctly enables the confirmation button.
- **shouldKeepConfirmButtonDisabledForIncorrectInput** *(edge case)* — Verifies that the confirmation button is not enabled unless the user types the exact required string "MERGE".
- **shouldCallOnConfirmWhenEnabledButtonIsClicked** — Tests that the `onConfirm` callback is triggered when the user completes the confirmation action.
- **shouldEnableMergeButtonWhenTwoDifferentOrganizationsAreSelected** — Verifies the primary happy path of the control component, allowing the user to proceed once valid selections are made.
- **shouldKeepMergeButtonDisabledIfSameOrganizationIsSelected** *(edge case)* — Tests the validation logic that prevents a user from merging an organization with itself.
- _(+1 more test cases)_

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This Product Requirements Document is the most critical source of information. It should define the data model, business rules, and constraints for the 'Organization' entity, which is essential for understanding how to merge records, permissions, and billing history correctly.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This overview describes the existing Organization Management tools. The new merge functionality will be an extension of this toolset, and this document provides context on the current user interface and administrative capabilities that the developer must align with.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be updated to include the new "Merge Organization" functionality, detailing the business rules for the suggestion engine and the data consolidation logic.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This document will need to be updated upon release to include instructions and details about the new organization merging feature for administrators.

## AI Confidence Scores
Plan: 80%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._