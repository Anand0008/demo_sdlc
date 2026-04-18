## IDRE-635: When navigating between Organizations Invoices are not getting loaded

**Jira Ticket:** [IDRE-635](https://orchidsoftware.atlassian.net//browse/IDRE-635)

## Summary
The bug is caused by the invoice list not refreshing upon switching organizations because the data-fetching logic in `InvoicesClientWrapper` does not react to this change. The plan is to make the component aware of the active organization using a shared hook and add the organization's ID to the `useEffect` dependency array to trigger a data re-fetch whenever the organization is changed. A regression test will be added to ensure the fix is effective.

## Implementation Plan

**Step 1: Make `InvoicesClientWrapper` aware of the active organization**  
The component needs to react to organization changes. This will be accomplished by using a shared hook that provides the currently active organization. You will need to import the application's hook for accessing the active organization (the exact name will need to be confirmed in the codebase, but it is likely in a shared hooks directory) and call it inside the `InvoicesClientWrapper` component to get the active organization's state.
Files: `app/app/invoices/components/invoices-client-wrapper.tsx`

**Step 2: Re-fetch invoices when the active organization changes**  
The `useEffect` hook that calls `fetchInvoices` currently runs only once because its dependencies (`fetchInvoices` and `organizations`) do not change after the initial render. The dependency array must be updated to include the active organization's ID to trigger a re-fetch when the user switches organizations. Locate the `useEffect` at line 42 and change its dependency array from `[fetchInvoices, organizations]` to `[fetchInvoices, activeOrganization?.id]`.
Files: `app/app/invoices/components/invoices-client-wrapper.tsx`

**Step 3: Add a regression test case**  
To prevent this bug from recurring, a test case should be added that simulates switching organizations and verifies that the invoice data is refetched. This involves mocking the active organization hook/provider and the `getPartyInvoices` server action, rendering the component, simulating a change in the active organization, and asserting that `getPartyInvoices` is called again.
Files: `tests/app/pages/app-invoices.test.ts`

**Risk Level:** LOW — The change is confined to a client-side component's data-fetching logic and its corresponding test file. It modifies *when* data is fetched, not *how* it's fetched or processed on the backend, which limits the potential for side effects.

## Proposed Code Changes

### `app/app/invoices/components/invoices-client-wrapper.tsx` (modify)
This change introduces the `useActiveOrganization` hook to make the component aware of the currently selected organization. The `useEffect` hook responsible for fetching invoices is updated to include the active organization's ID in its dependency array. This ensures that `fetchInvoices` is re-triggered whenever the user switches organizations, thus loading the correct data.
```
--- a/app/app/invoices/components/invoices-client-wrapper.tsx
+++ b/app/app/invoices/components/invoices-client-wrapper.tsx
@@ -1,6 +1,7 @@
 "use client";
 
 import { useCallback, useEffect, useMemo, useState } from "react";
+import { useActiveOrganization } from "@/lib/hooks/use-active-organization";
 
 import Link from "next/link";
 import { InvoicesTable } from "./invoices-table";
@@ -23,6 +24,7 @@
   viewOnly = false,
 }: InvoicesClientWrapperProps) {
   const router = useRouter();
+  const { activeOrganization } = useActiveOrganization();
   const [invoices, setInvoices] = useState<any[]>([]);
   const [isLoadingInvoices, setIsLoadingInvoices] = useState(false);
   const [search, setSearch] = useState("");
@@ -42,8 +44,10 @@
   }, []);
 
   useEffect(() => {
-    fetchInvoices();
-  }, [fetchInvoices, organizations]);
+    if (activeOrganization) {
+      fetchInvoices();
+    }
+  }, [fetchInvoices, activeOrganization?.id]);
 
   const filteredInvoices = useMemo(() => {
     const q = search.trim().toLowerCase();
```

### `tests/app/pages/app-invoices.test.ts` (modify)
This change adds a regression test to verify the bug fix. The test simulates a user switching between organizations and asserts that the `getPartyInvoices` action is called again, ensuring the invoice list is updated correctly. The existing mocks are updated to be more flexible to support this new test case.
```typescript
--- a/tests/app/pages/app-invoices.test.ts
+++ b/tests/app/pages/app-invoices.test.ts
@@ -1,19 +1,58 @@
-import { render, screen } from "@testing-library/react";
+import { render, screen, waitFor } from "@testing-library/react";
 import { InvoicesClientWrapper } from "@/app/app/invoices/components/invoices-client-wrapper";
 import { getPartyInvoices } from "@/lib/actions";
+import { useActiveOrganization } from "@/lib/hooks/use-active-organization";
 
 jest.mock("@/lib/actions", () => ({
+  ...jest.requireActual("@/lib/actions"),
   getPartyInvoices: jest.fn().mockResolvedValue([]),
 }));
 
 jest.mock("@/lib/hooks/use-active-organization", () => ({
-  useActiveOrganization: jest.fn().mockReturnValue({ activeOrganization: { id: "org_123", name: "Test Org" } }),
+  useActiveOrganization: jest.fn(),
 }));
 
+const mockGetPartyInvoices = getPartyInvoices as jest.Mock;
+const mockUseActiveOrganization = useActiveOrganization as jest.Mock;
+
 describe("Invoices Page", () => {
+  beforeEach(() => {
+    jest.clearAllMocks();
+  });
+
   it("renders the invoices table", () => {
+    mockUseActiveOrganization.mockReturnValue({
+      activeOrganization: { id: "org_123", name: "Test Org" },
+    });
     render(<InvoicesClientWrapper organizations={[]} />);
     expect(screen.getByText("No invoices yet")).toBeInTheDocument();
   });
+
+  it("should refetch invoices when the active organization changes", async () => {
+    // Arrange
+    const org1 = { id: "org_1", name: "Organization 1" };
+    const org2 = { id: "org_2", name: "Organization 2" };
+    const allOrgs = [org1, org2];
+
+    // Initial state: Org 1 is active
+    mockUseActiveOrganization.mockReturnValue({ activeOrganization: org1 });
+    mockGetPartyInvoices.mockResolvedValue([
+      { id: "inv_1", invoiceNumber: "INV-001", totalAmount: 100, status: "PAID" },
+    ]);
+
+    // Act
+    const { rerender } = render(<InvoicesClientWrapper organizations={allOrgs} />);
+
+    // Assert: Initial fetch for Org 1
+
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This Product Requirements Document (PRD) is the primary source for the business rules and expected functionality of the Organization Management feature. The ticket describes a bug that violates the core user experience of this feature, and this PRD defines what that experience should be.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview provides high-level context for the Organization Management feature. It helps the developer understand the scope and user-facing goals of the tool where the bug is occurring.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System

## AI Confidence Scores
Plan: 90%, Code: 85%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._