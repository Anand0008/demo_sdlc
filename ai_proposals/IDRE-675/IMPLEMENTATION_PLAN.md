## IDRE-675: Moving Case Organization - IP or NIP should default

**Jira Ticket:** [IDRE-675](https://orchidsoftware.atlassian.net//browse/IDRE-675)

## Summary
This plan implements the defaulting of the party role in the "Move Case Organization" modal. First, a `defaultPartyType` field will be added to the `Organization` model in the database schema. Then, backend actions will be updated to fetch this new field for both the list of available organizations and the current user's organization. Finally, the modal component will be modified to use the user's organization type to set the initial value of the "Change party role" dropdown.

## Implementation Plan

**Step 1: Update Database Schema for Organization Model**  
Add a new optional field `defaultPartyType` of type `String` to the `Organization` model. This field will store "IP" or "NIP" to indicate the organization's typical role. After adding the field, generate a new database migration.
Files: `prisma/schema.prisma`

**Step 2: Update Organization Search Action**  
Modify the `searchOrganizations` function to include the new `defaultPartyType` field in the returned organization data. This ensures that when organizations are fetched for the "New Organization" dropdown, their default party type is available to the frontend.
Files: `lib/actions/organization.ts`

**Step 3: Enhance Case Data Action to Return User's Org Type**  
Modify the server action that fetches the initial data for the organization assignment modal (likely `getCaseReviewData` or a similar function). This action should be updated to get the current user's session, find their primary organization, and return the organization's `defaultPartyType`. This will be passed to the modal as a prop to set the default value.
Files: `lib/actions/case-review.ts`

**Step 4: Implement Defaulting Logic in UI Modal**  
Update the `OrganizationData` interface to include the new `defaultPartyType` field. The component should accept the user's organization's party type as a new prop. Use this prop to set the initial state of the "Change party role" dropdown, defaulting to "IP" if the user's organization type is not available.
Files: `components/case-review/organization-assignments-edit-modal.tsx`

**Risk Level:** LOW — The changes involve adding a new optional field to the database and using it to default a UI element, which is unlikely to affect existing functionality. The main risk is the need for a database migration, which is a standard deployment procedure.
⚠️ **Database Migrations Required: YES**

**Deployment Notes:**
- A database migration is required to add the `defaultPartyType` column to the `Organization` table. This migration must be run during deployment.

## Proposed Code Changes

### `prisma/schema.prisma` (modify)
As per the implementation plan, a new optional field `defaultPartyType` is added to the `Organization` model. This will store whether an organization is typically an "IP" (Initiating Party) or "NIP" (Non-Initiating Party), which is the core data needed for the defaulting logic.
```
--- a/prisma/schema.prisma
+++ b/prisma/schema.prisma
@@ -1,5 +1,5 @@
 model Organization {
   id                   String                 @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
   name                 String
   type                 String                 @default("standard") // e.g., standard, enterprise
+  defaultPartyType     String?                @doc("Default party type for this organization, e.g., 'IP' or 'NIP'")
   createdAt            DateTime               @default(now())
   updatedAt            DateTime               @updatedAt
   members              Member[]
```

### `lib/actions/organization.ts` (modify)
The `searchOrganizations` server action is updated to include the new `defaultPartyType` field in its query results. This makes the default party type available to the frontend when a user searches for an organization to move a case to.
```typescript
--- a/lib/actions/organization.ts
+++ b/lib/actions/organization.ts
@@ -18,6 +18,7 @@
       id: true,
       name: true,
       type: true,
+      defaultPartyType: true,
     },
     take: 20,
   });
```

### `lib/actions/case-review.ts` (modify)
This change enhances the data-fetching action for the case review page. It now retrieves the current user's session, finds their primary organization, and returns that organization's `defaultPartyType`. This value will be passed to the UI modal to determine the default selection.
```typescript
--- a/lib/actions/case-review.ts
+++ b/lib/actions/case-review.ts
@@ -1,6 +1,7 @@
 "use server";
 
 import { prisma } from "@/lib/database";
+import { auth } from "@/lib/auth/server";
 import { revalidatePath } from "next/cache";
 import { getCasePermissions } from "@/lib/auth/permissions";
 
@@ -32,6 +33,18 @@
     throw new Error("Case not found");
   }
 
+  const session = await auth();
+  let userOrganizationDefaultPartyType: string | null = null;
+  if (session?.user?.organizationId) {
+    const userOrganization = await prisma.organization.findUnique({
+      where: { id: session.user.organizationId },
+      select: { defaultPartyType: true },
+    });
+    if (userOrganization) {
+      userOrganizationDefaultPartyType = userOrganization.defaultPartyType;
+    }
+  }
+
   return {
     caseId: caseData.id,
     initiatingParty: {
@@ -46,5 +59,6 @@
       organizationName: caseData.nonInitiatingParty.organization.name,
       organizationType: caseData.nonInitiatingParty.organization.type,
     },
+    userOrganizationDefaultPartyType,
   };
 }
```

### `components/case-review/organization-assignments-edit-modal.tsx` (modify)
The modal component is updated to implement the defaulting logic.
1.  The `OrganizationData` interface is extended to include `defaultPartyType`.
2.  A new prop, `userOrganizationDefaultPartyType`, is added to `OrganizationAssignmentsEditModalProps` to receive the user's organization type.
3.  The `newPartyRole` state is now initialized based on this new prop, defaulting to "NIP" if the user's organization type is "NIP", and "IP" otherwise. This directly implements the ticket's requirement.
```
--- a/components/case-review/organization-assignments-edit-modal.tsx
+++ b/components/case-review/organization-assignments-edit-modal.tsx
@@ -24,6 +24,7 @@
   id: string;
   name: string;
   type: string;
+  defaultPartyType?: string | null;
 }
 
 export interface OrganizationAssignmentsEditData {
@@ -63,18 +64,26 @@
     };
   };
   availableOrganizations: OrganizationData[];
+  userOrganizationDefaultPartyType?: string | null;
 }
 
 // Organization selector component - defined outside to prevent re-renders
@@ -100,12 +109,15 @@
   onComplete,
   initialData,
   availableOrganizations,
+  userOrganizationDefaultPartyType,
 }: OrganizationAssignmentsEditModalProps) {
   const [step, setStep] = useState(1);
   const [partyToChange, setPartyToChange] = useState<"IP" | "NIP" | null>(null);
   const [newOrganization, setNewOrganization] = useState<OrganizationData | null>(
     null
   );
-  const [newPartyRole, setNewPartyRole] = useState<"IP" | "NIP">("IP");
+  const [newPartyRole, setNewPartyRole] = useState<"IP" | "NIP">(
+    userOrganizationDefaultPartyType === "NIP" ? "NIP" : "IP"
+  );
   const [searchQuery, setSearchQuery] = useState("");
   const [searchResults, setSearchResults] = useState<OrganizationData[]>([]);
   const [isSearching, setIsSearching] = useState(false);
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Vitest`

- **shouldDefaultPartyRoleToNIPWhenUserOrganizationIsNIP** — Tests the primary happy path where the user's organization is a Non-Initiating Party (NIP), ensuring the dropdown defaults correctly.
- **shouldDefaultPartyRoleToIPWhenUserOrganizationIsIP** — Tests the happy path where the user's organization is an Initiating Party (IP), ensuring the dropdown defaults correctly.
- **shouldDefaultPartyRoleToIPWhenUserOrganizationTypeIsNotProvided** *(edge case)* — Covers the edge case where the user's organization does not have a default party type defined, ensuring the component falls back to a sensible default ("IP").
- **shouldAllowUserToChangePartyRoleAfterDefaulting** — This is a regression test to ensure that while the initial value is defaulted, the user can still override the selection.
- **shouldReturnUserOrganizationDefaultPartyTypeWhenSet** — Tests the backend logic in `lib/actions/case-review.ts` to ensure it correctly retrieves the user's organization and its default party type.
- **shouldIncludeDefaultPartyTypeInOrganizationSearchResults** — Validates that the change to `lib/actions/organization.ts` correctly includes the new `defaultPartyType` field in the data returned to the frontend.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the specific system being modified (Organization Management). It is the most likely source for business rules, data models, and constraints related to how organizations and their roles (IP/NIP) are defined and managed.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a high-level overview of the Organization Management feature. It can provide context on the intended user-facing behavior and the scope of the tool being modified.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be updated to include the new requirement for the IP/NIP role to default based on the selected organization's primary role.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This overview document should be updated to reflect the new, improved user experience where the party role defaults automatically.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._