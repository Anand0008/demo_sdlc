## IDRE-640: Organization Mismatch: Include Emails

**Jira Ticket:** [IDRE-640](https://orchidsoftware.atlassian.net//browse/IDRE-640)

## Summary
This plan details the implementation for adding party and organization emails to the IP/NIP Review page. It involves two main steps: first, updating the server action in `lib/actions/party-case-details.ts` to fetch the required email addresses from the database by expanding the Prisma query. Second, modifying the UI component in `app/app/cases/components/cases-page-client.tsx` to render this new information, including using a tooltip from `components/ui/tooltip.tsx` to display multiple organization emails. This plan carries a high risk due to the significant uncertainty in identifying the correct files from the limited context provided.

## Implementation Plan

**Step 1: Update Server Action to Fetch Email Data**  
In the `getCaseDetails` function, update the Prisma query to include the necessary email data. Specifically, for the party, include the related user's email. For both the current and suggested organizations, include the list of all associated users and their emails. The return type of the function will need to be updated to reflect these additions.
Files: `lib/actions/party-case-details.ts`

**Step 2: Update UI to Display Emails with Tooltip**  
Modify the component to display the newly fetched email addresses. Below the 'NIP/IP Party Name', render the party's email address. For the 'Current IP/NIP Org' and 'Current IP/NIP Suggested Org' columns, display the list of organization emails. If there is more than one email for an organization, use the `Tooltip` component from `components/ui/tooltip.tsx` to show the full list on hover. You will need to import `Tooltip`, `TooltipTrigger`, and `TooltipContent`.
Files: `app/app/cases/components/cases-page-client.tsx`, `components/ui/tooltip.tsx`

**Risk Level:** HIGH — The core risk is that the selected files are incorrect. The provided file context does not contain the specific server action or UI components for the IP/NIP Review tool, as evidenced by the exploration report and the rejection of a previous plan with logical file paths. The current plan is forced to assume that this admin tool reuses a party-facing action (`lib/actions/party-case-details.ts`) and component (`app/app/cases/components/cases-page-client.tsx`). If these assumptions are wrong, the implementation will not affect the target page at all, requiring a complete rework.

## Proposed Code Changes

### `lib/actions/party-case-details.ts` (modify)
This change modifies the `getCaseDetails` server action to fetch the necessary email addresses. It expands the Prisma query to include the party's user email and the list of emails for all users associated with both the current and suggested organizations. This provides the data required by the UI to fulfill the ticket's requirements.
```typescript
--- a/lib/actions/party-case-details.ts
+++ b/lib/actions/party-case-details.ts
@@ -15,28 +15,42 @@
       party: {
         include: {
           user: {
-            select: {
-              id: true,
-              name: true,
-            },
+            select: { id: true, name: true, email: true },
           },
         },
       },
       currentOrganization: {
-        select: {
-          id: true,
-          name: true,
+        include: {
+          users: {
+            select: {
+              email: true,
+            },
+            where: {
+              email: {
+                not: null,
+              },
+            },
+          },
         },
       },
       suggestedOrganization: {
-        select: {
-          id: true,
-          name:true,
+        include: {
+          users: {
+            select: {
+              email: true,
+            },
+            where: {
+              email: {
+                not: null,
+              },
+            },
+          },
         },
       },
     },
   });
 
   if (!partyCaseDetails) {
     return { data: null, error: "Case not found" };
```

### `app/app/cases/components/cases-page-client.tsx` (modify)
This change updates the UI to display the newly fetched email information. It adds the party's email directly below their name. For both the current and suggested organizations, it renders the associated emails. A helper function `renderOrgEmails` is introduced to handle the logic of displaying a single email directly or using a tooltip to show a list when multiple emails are present, as required by the ticket.
```
--- a/app/app/cases/components/cases-page-client.tsx
+++ b/app/app/cases/components/cases-page-client.tsx
@@ -3,6 +3,12 @@
 import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
 import { type getCaseDetails } from "@/lib/actions/party-case-details";
 import { Badge } from "@/components/ui/badge";
+import {
+  Tooltip,
+  TooltipContent,
+  TooltipProvider,
+  TooltipTrigger,
+} from "@/components/ui/tooltip";
 
 type CaseDetails = NonNullable<Awaited<ReturnType<typeof getCaseDetails>>["data"]>;
 
@@ -10,6 +16,33 @@
   caseDetails,
 }: {
   caseDetails: CaseDetails;
+}) {
+  const renderOrgEmails = (
+    users: { email: string | null }[] | undefined | null
+  ) => {
+    const emails = users?.map((u) => u.email).filter(Boolean) as string[] ?? [];
+    if (emails.length === 0) return null;
+
+    if (emails.length === 1) {
+      return <p className="text-sm text-muted-foreground">{emails[0]}</p>;
+    }
+
+    return (
+      <TooltipProvider>
+        <Tooltip>
+          <TooltipTrigger asChild>
+            <p className="text-sm text-muted-foreground cursor-pointer underline decoration-dotted">
+              {emails.length} emails
+            </p>
+          </TooltipTrigger>
+          <TooltipContent>
+            {emails.map((email) => (
+              <div key={email}>{email}</div>
+            ))}
+          </TooltipContent>
+        </Tooltip>
+      </TooltipProvider>
+    );
+  };
+
+  return (
+    <Card>
+      <CardHeader>
+        <CardTitle>Organization Mismatch Details</CardTitle>
+      </CardHeader>
+      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
+        <div className="space-y-1">
+          <p className="font-semibold">NIP/IP Party Name</p>
+          <p>{caseDetails.party.user?.name ?? "N/A"}</p>
+          {caseDetails.party.user?.email && (
+            <p className="text-sm text-muted-foreground">
+              {caseDetails.party.user.email}
+            </p>
+          )}
+        </di
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Vitest`

- **shouldReturnCaseDetailsWithPartyAndOrganizationEmails** — Verifies that the server action correctly queries and returns the case details including the newly added email fields for the party and associated organizations.
- **shouldHandleMissingEmailDataGracefully** *(edge case)* — Ensures the server action is resilient and does not crash when related email data is missing from the database.
- **shouldRenderPartyEmailWhenProvided** — Tests the happy path for displaying the NIP/IP party's email address when it is available in the data.
- **shouldRenderSingleOrganizationEmailDirectly** — Verifies that when only one organization email exists, it is displayed directly on the page without being hidden inside a tooltip.
- **shouldRenderMultipleOrganizationEmailsWithinATooltip** — Validates the requirement to use a tooltip to display the list of emails when an organization has more than one.
- **shouldRenderWithoutCrashingWhenEmailDataIsMissing** *(edge case)* — This edge case test ensures the component is robust and does not crash when the expected email data is missing or null in the props.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the Organization Management System, which is the feature being modified. It is the primary source for business rules, data models, and functional specifications a developer would need to consult before altering the system's behavior or UI.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a high-level overview and likely contains screenshots of the Organization Management feature. It will give the developer context on the current state of the UI they are being asked to modify.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: This PRD should be updated to reflect the new requirement of displaying party and organization emails in the UI.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: This document contains an overview of the feature and likely includes screenshots. It will need to be updated to reflect the UI changes showing organization emails.

## AI Confidence Scores
Plan: 30%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._