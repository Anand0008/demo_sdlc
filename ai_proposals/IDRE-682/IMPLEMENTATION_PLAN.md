## IDRE-682:  Improve Organization Dropdown Navigation in Banking Section for Main Org Users

**Jira Ticket:** [IDRE-682](https://orchidsoftware.atlassian.net//browse/IDRE-682)

## Summary
This plan improves the organization dropdown in the Banking section by introducing a clear visual hierarchy. First, the server action in `lib/party-actions.ts` will be updated to fetch and return organizations grouped by their main/sub-organization relationship. Next, the dropdown UI in `app/app/payments/components/payment-form.tsx` will be replaced with a more advanced combobox to display this hierarchy, complete with search functionality and a toggle to filter organizations without bank accounts. Finally, the main page component, `app/app/payments/page.tsx`, will be adjusted to handle the new data and update the section titles to clearly reflect the selected organization.

## Implementation Plan

**Step 1: Modify Server Action to Fetch Hierarchical Organization Data**  
Locate the server action responsible for fetching the list of organizations for the user. Modify the Prisma query to fetch not only the organizations but also their parent-child relationships and a flag indicating if they have an associated bank account. The function should return a structured list, grouping sub-organizations under their main organization, to be consumed by the frontend.
Files: `lib/party-actions.ts`

**Step 2: Implement Hierarchical Organization Dropdown with Search and Filtering**  
Replace the current flat `<Select>` component for organizations with a more advanced Combobox component. This new component will:
1.  Render the hierarchical data from the server action, with sub-organizations indented under their main organization.
2.  Include a search input field at the top of the dropdown to filter organizations by name.
3.  Add a toggle switch to show or hide organizations that do not have a bank account, based on the data provided by the server action.
4.  Implement a scrollable area with a fixed height to limit the number of visible items, as shown in the mockups.
Files: `app/app/payments/components/payment-form.tsx`

**Step 3: Integrate New Data Structure and Update Section Title**  
Update the `PaymentsPage` server component to call the modified server action to get the new hierarchical organization data and pass it to the `PaymentFormSection` and subsequently to the `PaymentForm`. Additionally, based on the `organizationId` from the search parameters, fetch the selected organization's details (name and if it's a sub-organization) to construct a more descriptive title for the `PaymentHistorySection` component (e.g., "Payment History for [Org Name]").
Files: `app/app/payments/page.tsx`

**Risk Level:** LOW — The changes are primarily on the UI and the data-fetching layer for a single feature. The risk is low as it doesn't alter core business logic for payments, but rather improves the user experience for selecting an organization. The main risk is ensuring the new data structure is handled correctly across the components.

## Proposed Code Changes

### `lib/party-actions.ts` (modify)
This change introduces a new server action, `getHierarchicalPartyOrganizations`, as outlined in the implementation plan. This function fetches all organizations a user has access to, along with their parent-child relationships and a count of their bank accounts. It then processes this flat list into a hierarchical structure, which is essential for the new combobox UI to render main organizations and their sub-organizations correctly. This new function is isolated to prevent breaking existing functionality that may rely on a flat list of organizations.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -1,5 +1,6 @@
 "use server";
 
+import "server-only";
 import { prisma } from "@/lib/prisma";
 import { getCurrentSession } from "@/lib/auth/utils";
 import { revalidatePath } from "next/cache";
@@ -10,6 +11,20 @@
   partyId: string;
   bankAccountId: string;
 }
+
+export type HierarchicalOrganization = {
+  id: string;
+  name: string;
+  hasBankAccount: boolean;
+  isSubParty: boolean;
+  subOrganizations: HierarchicalOrganization[];
+};
+
+/**
+ * Fetches all organizations accessible by the current user,
+ * structured hierarchically with main organizations and their sub-organizations.
+ * Also indicates whether each organization has a bank account.
+ */
 export async function getHierarchicalPartyOrganizations(): Promise<
   HierarchicalOrganization[]
 > {
@@ -27,6 +42,7 @@
       where: {
         users: {
           some: {
+            // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
             userId: session!.user.id,
           },
         },
@@ -35,8 +51,41 @@
       select: {
         id: true,
         name: true,
+        parentPartyId: true,
+        _count: {
+          select: { bankAccounts: true },
+        },
       },
     });
+
+    const orgsById = new Map(
+      allOrgs.map((org) => [
+        org.id,
+        {
+          id: org.id,
+          name: org.name,
+          hasBankAccount: org._count.bankAccounts > 0,
+          isSubParty: !!org.parentPartyId,
+          subOrganizations: [],
+        },
+      ])
+    );
+
+    const hierarchicalOrgs: HierarchicalOrganization[] = [];
+
+    for (const org of allOrgs) {
+      if (org.parentPartyId) {
+        const parent = orgsById.get(org.parentPartyId);
+        if (parent) {
+          // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
+          parent.subOrganizations.push(orgsById.get(org.id)!);
+        }
+      } else {
+        // eslint-disable-next-line @typescript-eslint/no-non-null-as
... (truncated — see full diff in files)
```

### `app/app/payments/page.tsx` (modify)
This change updates the main page component for the Banking section. It now calls the new `getHierarchicalPartyOrganizations` server action to fetch the structured organization data and passes it down to the `PaymentFormSection`. Additionally, it fetches the details of the currently selected organization to create a more descriptive title for the `PaymentHistorySection`, fulfilling a key requirement of the ticket to clarify which organization's data is being viewed.
```
--- a/app/app/payments/page.tsx
+++ b/app/app/payments/page.tsx
@@ -17,7 +17,9 @@
 } from "./components/loading-skeletons";
 import {
   getCasesForPayment,
+  getHierarchicalPartyOrganizations,
   getPartyUserBankAccounts as getUserBankAccounts,
+  getPartyById,
 } from "@/lib/actions";
 
 interface PaymentsPageProps {
@@ -55,6 +57,18 @@
   // Using paginated fetch to avoid Lambda timeout for large organizations.
   const INITIAL_PAGE_SIZE = 50;
 
+  const [organizations, selectedOrganization] = await Promise.all([
+    getHierarchicalPartyOrganizations(),
+    activeOrganizationId ? getPartyById(activeOrganizationId) : Promise.resolve(null),
+  ]);
+
+  const paymentHistoryTitle = selectedOrganization
+    ? `Payment History for ${selectedOrganization.name}`
+    : hasAllOrganizationsScope
+      ? "Payment History for All Organizations"
+      : "Payment History";
+
   // This promise is intentionally not awaited here. It's passed to the
   // suspense boundary to allow the UI to stream in.
   const casesPromise = getCasesForPayment({
@@ -101,7 +115,10 @@
             <Suspense fallback={<PaymentFormSkeleton />}>
               <PaymentFormSection
                 initialCasesPromise={casesPromise}
+                organizations={organizations}
                 activeOrganizationId={activeOrganizationId}
+                hasAllOrganizationsScope={hasAllOrganizationsScope}
                 viewOnly={viewOnly}
               />
             </Suspense>
@@ -112,7 +129,7 @@
           <div className="col-span-12 lg:col-span-8">
             <Suspense fallback={<PaymentHistorySkeleton />}>
               <PaymentHistorySection
-                title="Payment History"
+                title={paymentHistoryTitle}
                 organizationId={activeOrganizationId}
               />
             </Suspense>
```

### `app/app/payments/components/payment-form.tsx` (modify)
This is the core UI change. The existing simple `<Select>` component for choosing an organization is replaced with a much more powerful `Combobox` built from `shadcn/ui`'s `Popover` and `Command` components. This new implementation directly addresses the ticket's requirements by:
1.  Rendering a hierarchical list using `CommandGroup` for main organizations and indentation for sub-organizations.
2.  Including a `CommandInput` for real-time searching.
3.  Adding a `Switch` to toggle the visibility of organizations that do not have a bank account.
4.  Updating the URL via `next/navigation`'s `useRouter` when a new organization is selected, triggering a data refresh for the entire page.
This change provides the rich, user-friendly navigation experience requested in the ticket.
```
--- a/app/app/payments/components/payment-form.tsx
+++ b/app/app/payments/components/payment-form.tsx
@@ -1,6 +1,6 @@
 "use client";
 
-import { useState, useCallback, useEffect, useMemo, useRef } from "react";
+import { useState, useCallback, useEffect, useMemo, useRef, Fragment } from "react";
 import { useRouter } from "next/navigation";
 import { useForm } from "react-hook-form";
 import { zodResolver } from "@hookform/resolvers/zod";
@@ -14,6 +14,15 @@
   SelectTrigger,
   SelectValue,
 } from "@/components/ui/select";
+import {
+  Command,
+  CommandEmpty,
+  CommandGroup,
+  CommandInput,
+  CommandItem,
+  CommandList,
+} from "@/components/ui/command";
+import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
 import { Badge } from "@/components/ui/badge";
 import { Separator } from "@/components/ui/separator";
 import { Input } from "@/components/ui/input";
@@ -36,12 +45,15 @@
   CheckCircle,
   Search,
   ArrowRight,
+  ChevronsUpDown,
   Check,
   FileText,
   Info,
   Download,
 } from "lucide-react";
 import { toast } from "sonner";
+import { Switch } from "@/components/ui/switch";
 import { processBulkPayment } from "@/lib/actions";
 import { fetchMoreCasesForPayment, downloadCasesForPaymentCsv } from "@/lib/actions";
 import { StripePaymentForm } from "@/components/stripe-payment-form";
@@ -51,6 +63,7 @@
   buildSharedBankAccountGroups,
   type SharedBankAccountGroup,
 } from "@/lib/payments/shared-bank-account-groups";
+import type { HierarchicalOrganization } from "@/lib/party-actions";
 
 const bankAccountSelectionSchema = z.object({
   organizationId: z.string(),
@@ -101,6 +114,7 @@
 
 interface PaymentFormProps {
   initialCases: CaseForPayment[];
+  organizations: HierarchicalOrganization[];
   totalCaseCount: number;
   activeOrganizationId: string | null;
   hasAllOrganizationsScope: boolean;
@@ -110,6 +124,7 @@
 
 export function PaymentForm({
   initialCases,
+  organizations,
   totalCaseCount,
   activeOrganizati
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Vitest`

- **shouldRenderOrganizationsInHierarchicalGroups** — Verifies that the new Combobox correctly displays main organizations as non-selectable group headings and their sub-organizations as selectable items, establishing a clear visual hierarchy.
- **shouldFilterOrganizationsOnSearch** — Ensures the search functionality within the combobox correctly filters the list of organizations, allowing users to find a specific sub-organization by name quickly.
- **shouldUpdateUrlOnOrganizationSelection** — Validates that selecting a sub-organization triggers a URL update, which is the mechanism for refreshing the page data to show the selected organization's banking details.
- **shouldToggleVisibilityOfOrgsWithNoBankAccounts** *(edge case)* — Tests the functionality of the switch that allows users to show or hide organizations that do not have a bank account.
- **shouldCorrectlyStructureHierarchicalData** — Verifies the core logic of the server action, ensuring it correctly transforms a flat list of organizations into a nested, hierarchical structure based on parent-child relationships.
- **shouldHandleFlatListWithNoSubOrganizations** *(edge case)* — Tests the edge case where there are no sub-organizations, ensuring the function handles the data gracefully without errors.
- **shouldFetchDataAndRenderCorrectSectionTitles** — Ensures the main page component correctly fetches data from the new server action, passes it to the form, and uses it to create a descriptive title for the payment history section.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the core Product Requirements Document (PRD) for the Organization Management feature. It defines the fundamental business rules, data model (main vs. sub-organizations), and user roles that the ticket's UI improvements must be built upon. It explicitly mentions the concept of an "Organization Dropdown" for selecting between main and sub-organizations.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be updated to include the new UI/UX requirements for the banking section's organization dropdown, including the hierarchical display, search functionality, and visual treatment of main vs. sub-organizations.

## AI Confidence Scores
Plan: 90%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._