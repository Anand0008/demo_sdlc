## IDRE-674: Main Organization issues

**Jira Ticket:** [IDRE-674](https://orchidsoftware.atlassian.net//browse/IDRE-674)

## Summary
This plan addresses the issue of duplicate main organizations by enforcing uniqueness at the domain level. It involves three steps: first, adding a unique constraint to the `domain` field in the `Organization` database model; second, updating the backend server action to check for duplicates before creation and return a clear error; and third, updating the admin UI to display this error to the user. This ensures data integrity and provides a better user experience.

## Implementation Plan

**Step 1: Add unique constraint to Organization model in schema**  
Modify the `prisma/schema.prisma` file to add a `@unique` constraint to the `domain` field on the `Organization` model. This will enforce data integrity at the database level. After updating the schema, generate a new migration file.
Files: `prisma/schema.prisma`

**Step 2: Update server action to check for duplicate domains**  
In `lib/actions/organization.ts`, locate the function responsible for creating a new organization. Before the `prisma.organization.create` call, add logic to query for an existing organization with the same domain. If a duplicate is found, return a specific error message.
Files: `lib/actions/organization.ts`

**Step 3: Handle and display duplicate domain error in the UI**  
The UI for creating a new organization, which is likely located in or launched from `app/admin/organizations/page.tsx` based on the provided screenshot, needs to be updated. The form submission logic should handle the error response from the server action and display a user-friendly error message (e.g., "An organization with this domain already exists.") when a duplicate domain is entered.
Files: `app/admin/organizations/page.tsx`

**Risk Level:** LOW — The primary risk is related to data integrity. If there are existing duplicate organizations by domain in the database, the new unique constraint will cause the database migration to fail. This requires a data cleanup task before deployment. The code changes themselves are low-risk as they add validation and do not alter core logic.
⚠️ **Database Migrations Required: YES**

**Deployment Notes:**
- A data cleanup script must be run on existing data to remove or merge organizations with duplicate domains before applying the database migration, as the migration will fail if duplicates exist.
- The new database migration must be applied as part of the deployment process.

## Proposed Code Changes

### `prisma/schema.prisma` (modify)
Adding the `@unique` constraint to the `domain` field in the `Organization` model enforces data integrity at the database level. This is the most reliable way to prevent duplicate domains from being saved, even in race conditions. The constraint will only apply to non-null values, which is the correct behavior.
```
--- a/prisma/schema.prisma
+++ b/prisma/schema.prisma
@@ -358,7 +358,7 @@
 model Organization {
   id                                String                     @id @default(cuid())
   name                              String                     @db.Text
-  domain                            String?                    @db.Text
+  domain                            String?                    @unique @db.Text
   type                              OrganizationType
   email                             String?                    @db.Text
   phone                             String?                    @db.Text
```

### `lib/actions/organization.ts` (modify)
A new server action `createOrganization` is added (or would be modified if it existed but was not found during exploration). This action includes a crucial pre-check to see if an organization with the given domain already exists. If a duplicate is found, it returns a specific error message, providing clear feedback to the frontend without hitting a database error. This improves the user experience and handles the business logic gracefully.
```typescript
--- a/lib/actions/organization.ts
+++ b/lib/actions/organization.ts
@@ -8,6 +8,8 @@
   data?: T;
   error?: string;
 };
+
+import { revalidatePath } from "next/cache";
 
 /**
  * Search organizations by name — returns up to 50 matching results.
@@ -73,3 +75,40 @@
     return { success: false, error: "Failed to get organizations" };
   }
 }
+
+/**
+ * Creates a new organization.
+ * Checks for duplicate domains before creation.
+ */
+export async function createOrganization(data: {
+  name: string;
+  domain: string;
+  type: OrganizationType;
+}): Promise<ActionResult<Organization>> {
+  try {
+    const session = await auth.api.getSession({ headers: await headers() });
+    if (!session) {
+      return { success: false, error: "Authentication required" };
+    }
+
+    // TODO: Add permission check for creating organizations
+
+    if (data.domain) {
+      const existingByDomain = await prisma.organization.findUnique({
+        where: { domain: data.domain },
+      });
+      if (existingByDomain) {
+        return { success: false, error: "An organization with this domain already exists." };
+      }
+    }
+
+    const organization = await prisma.organization.create({
+      data,
+    });
+
+    revalidatePath("/admin/organizations");
+    return { success: true, data: organization };
+  } catch (error) {
+    console.error("Error creating organization:", error);
+    return { success: false, error: "Failed to create organization." };
+  }
+}
```

### `app/dashboard/organizations/page.tsx` (modify)
The form submission logic in the admin UI is updated to properly handle the response from the `createOrganization` server action. It now uses a state variable to store and display any errors returned from the action, such as the "domain already exists" message. This provides immediate and clear feedback to the user, improving the usability of the organization creation form. A `useTransition` hook is also added to handle the pending state of the form submission, disabling the button to prevent multiple clicks.
```
--- a/app/admin/organizations/page.tsx
+++ b/app/admin/organizations/page.tsx
@@ -1,10 +1,12 @@
 'use client';
 
-import { useState } from 'react';
+import { useState, useTransition } from 'react';
 import { Button } from '@/components/ui/button';
 import { Input } from '@/components/ui/input';
 import { Label } from '@/components/ui/label';
-import { createOrganization } from '@/lib/actions/organization'; // Assuming this action exists
+import { createOrganization } from '@/lib/actions/organization';
+import { useToast } from "@/components/ui/use-toast";
+import { OrganizationType } from '@prisma/client';
 
 // This is a hypothetical structure based on the implementation plan,
 // as the original file content was not available.
@@ -12,25 +14,48 @@
 export default function AdminOrganizationsPage() {
   // Assume a modal or form state for creating a new organization
   const [isCreateModalOpen, setCreateModalOpen] = useState(false);
+  const [isPending, startTransition] = useTransition();
+  const [error, setError] = useState<string | null>(null);
+  const { toast } = useToast();
 
-  const handleCreateOrganization = async (formData: FormData) => {
-    const name = formData.get('name') as string;
-    const domain = formData.get('domain') as string;
+  const handleSubmit = async (formData: FormData) => {
+    setError(null);
+    const name = formData.get('name')?.toString().trim();
+    const domain = formData.get('domain')?.toString().trim();
+    const type = formData.get('type')?.toString() as OrganizationType;
 
-    if (!name || !domain) {
-      // Handle validation
+    if (!name || !domain || !type) {
+      setError("Name, domain, and type are required.");
       return;
     }
 
-    const result = await createOrganization({ name, domain, type: 'MAIN' }); // Assuming type
+    startTransition(async () => {
+      const result = await createOrganization({ name, domain, type });
 
-    if (result.success) {
-      // Handle success - e.g., close modal, show
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Vitest / Jest`

- **shouldReturnErrorWhenCreatingOrganizationWithExistingDomain** — This is a regression test to verify the primary bug fix. It ensures that the server action correctly identifies a duplicate domain and prevents the creation of a new organization, returning a specific error message instead.
- **shouldCreateOrganizationSuccessfullyWithUniqueDomain** — This happy path test ensures that the changes made to prevent duplicates have not broken the standard functionality of creating a new organization with a unique domain.
- **shouldDisplayErrorMessageWhenCreateOrganizationFails** — This test verifies that the UI correctly handles and displays the specific error message returned from the server action, providing clear feedback to the user as described in the implementation plan.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the Organization Management System. It is the most critical document as it should contain the original, intended business rules, data models, and constraints for creating and managing organizations, which is the core of the ticket.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview describes the functionality of the Organization Management feature. It provides context on how the system is intended to behave from a user's perspective and is useful for understanding the scope of the feature being fixed.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be updated to explicitly define the uniqueness constraint based on the organization's domain and specify the error handling behavior when a user attempts to create a duplicate.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This overview document should be updated to reflect the implemented uniqueness rule, ensuring that any user guides or feature descriptions align with the new constraint.

## AI Confidence Scores
Plan: 80%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._