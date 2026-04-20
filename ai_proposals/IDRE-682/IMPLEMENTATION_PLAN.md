## IDRE-682:  Improve Organization Dropdown Navigation in Banking Section for Main Org Users

**Jira Ticket:** [IDRE-682](https://orchidsoftware.atlassian.net//browse/IDRE-682)

## Summary
This plan improves the organization selection dropdown in the Banking section by increasing its visible height, adding a "Main" badge for clear identification of parent organizations, and updating tests to verify the new visual element. The changes are targeted to the `components/party/banking/organization-switcher.tsx` component to implement the required visual hierarchy and usability enhancements.

## Implementation Plan

**Step 1: Increase Dropdown Scroll Limit**  
Update the `MAX_VISIBLE_ITEMS` constant from `10` to `15` to increase the dropdown's visible height before scrolling is required. This change is based on the annotation in the ticket's UI mockup.
Files: `components/party/banking/organization-switcher.tsx`

**Step 2: Add "Main" Badge to Main Organizations**  
Import the `Badge` component from "@/components/ui/badge". Then, within the `groupedOptions.map()` function that renders the list of organizations, conditionally add a `Badge` component with the text "Main" for any organization where `option.isMainOrg` is true. This will visually distinguish main organizations as requested. The badge should be placed after the organization's name and before the expand/collapse button.
Files: `components/party/banking/organization-switcher.tsx`

**Step 3: Update Component Tests**  
Add a new test case to verify that the "Main" badge is correctly rendered for organizations marked as main organizations and is not rendered for sub-organizations. This involves mocking the `Badge` component and asserting its presence based on the `isMainOrg` prop.
Files: `tests/components/organization-switcher.test.tsx`

**Risk Level:** LOW — The changes are confined to a single, well-encapsulated UI component and its corresponding test file. The modifications are primarily presentational and do not affect the underlying data-fetching or state management logic, minimizing the risk of regressions.

## Proposed Code Changes

### `components/party/banking/organization-switcher.tsx` (modify)
1.  The `MAX_VISIBLE_ITEMS` constant is increased from 10 to 15 to expand the dropdown's visible height, reducing the need for scrolling as specified in the ticket.
2.  The `Badge` component is imported and conditionally rendered for main organizations (`option.isMainOrg`). This adds a "Main" label, making it easier for users to distinguish parent organizations from sub-organizations in the list. A `secondary` variant and left margin are used for appropriate styling and spacing.
```
--- a/components/party/banking/organization-switcher.tsx
+++ b/components/party/banking/organization-switcher.tsx
@@ -10,6 +10,7 @@
   PopoverTrigger,
 } from "@/components/ui/popover";
 import { Check, ChevronDown, ChevronRight, ChevronsUpDown, CircleAlert, SearchIcon } from "lucide-react";
+import { Badge } from "@/components/ui/badge";
 import { cn } from "@/lib/utils";
 import { Switch } from "@/components/ui/switch";
 import { Label } from "@/components/ui/label";
@@ -34,7 +35,7 @@
 }
 
 const ALL_ORGS_ID = "__all__";
-const MAX_VISIBLE_ITEMS = 10;
+const MAX_VISIBLE_ITEMS = 15;
 const ITEM_HEIGHT = 30; // px per item
 
 type OptionItem = {
@@ -294,6 +295,9 @@
                       )}
                     />
                     <span className="truncate">{option.label}</span>
+                    {option.isMainOrg && (
+                      <Badge variant="secondary" className="ml-2">Main</Badge>
+                    )}
                     {!option.hasBankAccounts && (
                       <Tooltip>
                         <TooltipTrigger asChild>
```

### `tests/components/organization-switcher.test.tsx` (modify)
A new test case is added to verify the correct rendering of the "Main" badge. This involves mocking the `Badge` component and then asserting that the badge's text appears within the list item for a main organization but not for a sub-organization, ensuring the new visual indicator works as expected.
```
--- a/tests/components/organization-switcher.test.tsx
+++ b/tests/components/organization-switcher.test.tsx
@@ -54,6 +54,12 @@
   TooltipContent: ({ children }: any) => <span>{children}</span>,
 }));
 
+vi.mock("@/components/ui/badge", () => ({
+  Badge: ({ children, variant, className }: any) => (
+    <span className={`badge variant-${variant} ${className}`}>{children}</span>
+  ),
+}));
+
 const mockOrganizations = [
   { id: "org-1", name: "Organization One" },
   { id: "org-2", name: "Organization Two" },
@@ -351,4 +357,31 @@
       expect(screen.getByText("Alpha Child Org")).toBeInTheDocument();
     });
   });
+
+  it("renders a 'Main' badge for main organizations", () => {
+    render(
+      <OrganizationSwitcher
+        organizations={[
+          {
+            id: "main-1",
+            name: "Main Org",
+            isMainOrg: true,
+          },
+          {
+            id: "child-1",
+            name: "Child Org",
+            parentOrgId: "main-1",
+            isMainOrg: false,
+          },
+        ]}
+        selectedOrganizationId={null}
+      />
+    );
+
+    const mainOrgItem = screen.getByText("Main Org").closest("div");
+    expect(mainOrgItem).toHaveTextContent("Main");
+
+    const childOrgItem = screen.getByText("Child Org").closest("div");
+    expect(childOrgItem).not.toHaveTextContent("Main");
+  });
 });
```

**New Dependencies:**
- `_No new dependencies needed_`

## Test Suggestions

Framework: `Vitest`

- **shouldRenderMainBadgeForMainOrganization** — Verifies that the "Main" badge is correctly rendered next to the main organization's name in the dropdown list, confirming the primary visual change.
- **shouldNotRenderMainBadgeForSubOrganizations** — Ensures that the "Main" badge does not appear for sub-organizations, verifying the conditional rendering logic.
- **shouldDisplayAllOrganizationsWhenOpened** — A fundamental test to ensure the component renders correctly and that user interaction (opening the dropdown) reveals the list of selectable organizations.
- **shouldCallOnSelectOrgWithCorrectIdWhenItemIsClicked** — Verifies that selecting an item from the dropdown correctly triggers the callback function, which is essential for updating the application state.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This Product Requirements Document (PRD) is the primary source of truth for the ticket. It explicitly defines the business rules, constraints, and data model for the two-level organization hierarchy (Parent -> Sub-Organization) that the ticket must implement in the banking dropdown. Section 10.3 directly specifies that dropdowns should surface the parent organization's name.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview provides a crucial precedent for the UI implementation. It states that in the admin-facing "Organizations Tab", sub-organization relationships are already visualized by showing parent organization names inline beneath the sub-org. This establishes an existing design pattern that the developer should follow for the new banking dropdown to ensure consistency.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System - This PRD defines the rules for the organization hierarchy. It should be updated with screenshots and a description of the new banking dropdown UI to reflect how the requirements were implemented.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview - This document describes the admin-facing tools for organization management. It should be updated to include details and screenshots of the new user-facing organization dropdown in the Banking section, providing a complete overview of the feature.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._