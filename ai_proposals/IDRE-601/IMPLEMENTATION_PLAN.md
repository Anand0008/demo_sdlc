## IDRE-601: User is able to upload case by selecting same Organization for both IP and NIP

**Jira Ticket:** [IDRE-601](https://orchidsoftware.atlassian.net//browse/IDRE-601)

## Summary
This plan will fix the bug allowing the same organization to be selected for both parties in a case by adding a robust server-side validation check to the `createCase` action in `lib/actions/case.ts`. This check will inspect the raw form data before any complex organization resolution logic can obscure the user's original selection. A new regression test will be added to `tests/actions/case-validation.test.ts` to verify the fix and prevent future regressions.

## Implementation Plan

**Step 1: Add server-side validation to `createCase` action**  
In the `createCase` function, before the calls to `resolveOrganizationSelection` (around line 446), add a new validation block. This block will check the raw `formData` to prevent the same organization from being used for both parties, either by selecting the same existing organization or by creating two new organizations with the same name. This preempts the `resolveOrganizationSelection` logic which could otherwise mask the issue by creating a new organization.

```typescript
// Add this block before line 447 in lib/actions/case.ts

if (
  formData.initiatingOrganizationMode === "existing" &&
  formData.nonInitiatingOrganizationMode === "existing" &&
  formData.initiatingOrganizationId &&
  formData.initiatingOrganizationId === formData.nonInitiatingOrganizationId
) {
  return {
    success: false,
    error: "Initiating Party and Non-Initiating Party cannot be the same organization.",
  };
}

if (
  formData.initiatingOrganizationMode === "new" &&
  formData.nonInitiatingOrganizationMode === "new" &&
  formData.initiatingOrganizationName &&
  formData.nonInitiatingOrganizationName &&
  formData.initiatingOrganizationName.trim().toLowerCase() === formData.nonInitiatingOrganizationName.trim().toLowerCase()
) {
    return {
        success: false,
        error: "The new organization name for the Initiating Party cannot be the same as the Non-Initiating Party.",
    };
}
```
Files: `lib/actions/case.ts`

**Step 2: Add regression test for same-organization validation**  
Add a new test suite to this file to cover the `createCase` action's validation logic. Create a new test case that attempts to create a case with the same existing organization ID for both the initiating and non-initiating parties. Assert that the `createCase` action returns a failure result with the specific error message, ensuring the new server-side validation is working correctly and preventing regressions.
Files: `tests/actions/case-validation.test.ts`

**Risk Level:** LOW — The change is an additive validation check at the beginning of a server action. It does not alter the existing logic for valid data, only rejects invalid submissions earlier. The risk of unintended side effects is minimal. An accompanying regression test will further ensure correctness.

## Proposed Code Changes

### `lib/actions/case.ts` (modify)
This change adds a server-side validation check at the beginning of the `createCase` action. It inspects the raw form data to ensure that if two existing organizations are selected, their IDs are different, and if two new organizations are being created, their names are different (case-insensitively). This prevents the bug described in the ticket at the earliest possible point, before any complex organization resolution logic is executed.
```typescript
--- a/lib/actions/case.ts
+++ b/lib/actions/case.ts
@@ -443,6 +443,32 @@
     const initiatingPartyEmails = collectPartyEmails(initiatingPartyInfo);
     const nonInitiatingPartyEmails = collectPartyEmails(nonInitiatingPartyInfo);
 
+    // IDRE-601: Prevent selecting the same organization for both parties from the form data directly.
+    // This check is performed before `resolveOrganizationSelection` to catch the user's
+    // direct input, as the resolution logic might create new organizations and mask the issue.
+    if (
+      formData.initiatingOrganizationMode === "existing" &&
+      formData.nonInitiatingOrganizationMode === "existing" &&
+      formData.initiatingOrganizationId &&
+      formData.initiatingOrganizationId === formData.nonInitiatingOrganizationId
+    ) {
+      return {
+        success: false,
+        error: "Initiating Party and Non-Initiating Party cannot be the same organization.",
+      };
+    }
+
+    if (
+      formData.initiatingOrganizationMode === "new" &&
+      formData.nonInitiatingOrganizationMode === "new" &&
+      formData.initiatingOrganizationName &&
+      formData.nonInitiatingOrganizationName &&
+      formData.initiatingOrganizationName.trim().toLowerCase() === formData.nonInitiatingOrganizationName.trim().toLowerCase()
+    ) {
+        return {
+            success: false,
+            error: "The new organization name for the Initiating Party cannot be the same as the Non-Initiating Party.",
+        };
+    }
+
     const initiatingSelection = await resolveOrganizationSelection({
       mode: formData.initiatingOrganizationMode,
       organizationId: formData.initiatingOrganizationId,
```

### `tests/actions/case-validation.test.ts` (modify)
This change adds a new test suite to validate the `createCase` server action. It specifically adds regression tests for the scenario where the same organization is selected for both parties, either by ID for existing organizations or by name for new ones. The necessary mocks for authentication and other dependencies are updated to allow the action to run up to the point of validation.
```typescript
--- a/tests/actions/case-validation.test.ts
+++ b/tests/actions/case-validation.test.ts
@@ -1,10 +1,26 @@
-import { describe, it, expect, vi } from "vitest";
+import { describe, it, expect, vi, beforeEach } from "vitest";
+import { createCase } from "@/lib/actions/case";
+import type { CaseWizardFormData } from "@/lib/utils/case-wizard-schema";
+import { auth } from "@/lib/auth/server";
+import { headers } from "next/headers";
+import { isFeatureFlagEnabled } from "@/lib/posthog/server";
 
 // Mock external dependencies
-vi.mock("@/lib/database", () => ({ prisma: {} }));
-vi.mock("@/lib/auth/server", () => ({ auth: { api: {} } }));
+vi.mock("@/lib/database", () => ({
+  prisma: {
+    $transaction: vi.fn((callback) => callback(vi.fn())),
+  },
+}));
+vi.mock("@/lib/auth/server", () => ({
+  auth: {
+    api: {
+      getSession: vi.fn(),
+      userHasPermission: vi.fn(),
+    },
+  },
+}));
 vi.mock("next/headers", () => ({ headers: vi.fn() }));
 vi.mock("next/cache", () => ({ revalidatePath: vi.fn() }));
 vi.mock("@/lib/events/emitters", () => ({
@@ -35,6 +51,10 @@
 vi.mock("@/lib/actions/party-member-management", () => ({
   applyGlobalMembersToOrganization: vi.fn(),
 }));
+vi.mock("@/lib/posthog/server", () => ({
+  isFeatureFlagEnabled: vi.fn().mockResolvedValue(false),
+  capturePerformanceBestEffort: vi.fn(),
+}));
 
 // We need to test the internal validation functions
 // Since they're not exported, we test them through createCase or by testing the patterns directly
@@ -187,3 +207,58 @@
     });
   });
 });
+
+describe("createCase action validation", () => {
+  beforeEach(() => {
+    vi.clearAllMocks();
+
+    const mockSession = {
+      user: { id: "user-123", name: "Test User", email: "test@example.com", role: "admin" },
+    };
+    const mockHeaders = new Map();
+    (headers as vi.Mock).mockReturnValue(mockHeaders);
+    (auth.api.getSession as vi.Mock).mockResolvedValue(mockSession);
+    (auth.api.userHasPermission as vi.Mock).mockResolvedValue({ s
... (truncated — see full diff in files)
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Jest`

- **shouldReturnErrorWhenSameExistingOrgIsSelectedForBothParties** — This test reproduces the core bug where a user selects the same existing organization for both the IP and NIP parties. It ensures the new server-side validation catches this and prevents case creation.
- **shouldReturnErrorWhenSameNewOrgNameIsUsedForBothParties** *(edge case)* — This test covers the second scenario identified in the bug fix, where a user attempts to create two new organizations with the same name for a single case. It validates that the check is case-insensitive as per the implementation.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD provides the foundational business logic for the ticket. The "Actor Model" explicitly defines the Initiating Party (IP) and Non-Initiating Party (NIP) as distinct and opposing entities (Provider vs. Insurer). This is the core business rule the ticket must enforce. Section 10.3 also discusses UX warnings for mismatched IP/NIP assignments.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This page is relevant because it describes an existing administrative tool built specifically to find and correct IP/NIP assignment errors *after* they have been made. The existence of this tool proves the business importance of preventing these errors at the source, which is the purpose of ticket IDRE-601.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This document defines the canonical workflow for the entire platform and reinforces the fundamental business rule that the IP (provider) and NIP (insurer) are separate and distinct external parties in any dispute. The ticket enforces this separation at the data entry level.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: The technical/UX requirements (section 10.3) should be updated to explicitly state that the system must prevent the same organization from being selected for both IP and NIP roles.
- Pre-Staging Readiness and End-to-End Testing Workflow for Development and QA Team: The QA checklist for "Case Initiation & Upload" should be updated with a new test case to verify that a user cannot select the same organization for both IP and NIP.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._