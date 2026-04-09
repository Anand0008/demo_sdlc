## IDRE-479: Case Creation: Organization Selection

**Jira Ticket:** [IDRE-479](https://orchidsoftware.atlassian.net//browse/IDRE-479)

## Summary
Update the case creation organization selection step to display parsed IP/NIP details, enforce a strict 90% similarity threshold for organization suggestions, and auto-populate exact matches while falling back to a search field.

## Implementation Plan

**Step 1: Display Parsed Organization Data in UI**  
Retrieve the parsed IP and NIP Organization Name and Email Address from the form state. Add a UI element (e.g., a callout or informational card) at the top of both the IP and NIP selection sections to clearly display these parsed values to the user.
Files: `components/case-wizard/step-organization.tsx`

**Step 2: Enforce 90% Similarity Threshold for Organization Suggestions**  
Update the organization suggestion and filtering logic to enforce a strict 90% match threshold. Use the existing `calculateSimilarity` function and filter out any organizations where the similarity score is `< 0.9`. If no organizations meet this threshold, display a 'No match found' state that prompts the user to create a new organization.
Files: `components/case-wizard/step-organization.tsx`

**Step 3: Implement Exact Match Auto-population and Search Fallback**  
Implement logic to check for an exact (1-to-1) name match between the parsed organization name and the registered organizations. If an exact match is found, automatically select it and populate the email address field. If no exact match is found, ensure the UI defaults to displaying the search field instead of a pre-populated list.
Files: `components/case-wizard/step-organization.tsx`

**Risk Level:** LOW — The changes are isolated to the frontend organization selection step of the case creation wizard. They refine existing fuzzy-matching logic and add UI elements without altering backend data structures or core case creation mutations.

## Proposed Code Changes

### `components/case-wizard/step-organization.tsx` (modify)
- **Parsed Data Display**: Added a `ParsedDataDisplay` component to clearly show the parsed organization name and email at the top of the selection section, fulfilling the requirement to display IP and NIP details.
- **90% Similarity Threshold**: Updated the similarity threshold in the `suggestedOrgs` memoization to `>= 0.9` to enforce the strict 90% match criteria. This ensures that a list of potential organizations whose names do not match with at least 90% criteria is not presented.
- **Exact Match Auto-population**: Added a `useEffect` hook to automatically find an exact match (1-to-1) and populate the organization ID and email address in the form. If no exact match is found, the UI will naturally fall back to the search field since `suggestedOrgs` will be empty or only contain >=90% matches.
```
--- a/components/case-wizard/step-organization.tsx
+++ b/components/case-wizard/step-organization.tsx
@@ -48,6 +48,28 @@
 } from "@/components/ui/dialog"
 import { Check, ChevronsUpDown, Loader2, Search, Sparkles, AlertTriangle } from "lucide-react"
 
 const MIN_SEARCH_LENGTH = 2
 
+// UI Component to display parsed organization data
+function ParsedDataDisplay({ name, email, partyType }: { name?: string, email?: string, partyType: 'IP' | 'NIP' }) {
+  if (!name && !email) return null;
+  return (
+    <div className="mb-6 p-4 bg-blue-50/50 dark:bg-blue-950/20 rounded-lg border border-blue-100 dark:border-blue-900">
+      <div className="flex items-center gap-2 mb-3">
+        <Sparkles className="h-4 w-4 text-blue-600 dark:text-blue-400" />
+        <h4 className="text-sm font-medium text-blue-900 dark:text-blue-300">Parsed {partyType} Information</h4>
+      </div>
+      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
+        <div>
+          <span className="text-muted-foreground block mb-1">Organization Name</span>
+          <p className="font-medium">{name || "Not found in document"}</p>
+        </div>
+        <div>
+          <span className="text-muted-foreground block mb-1">Email Address</span>
+          <p className="font-medium">{email || "Not found in document"}</p>
+        </div>
+      </div>
+    </div>
+  );
+}
+
 // String similarity utility - calculates similarity between two strings (0-1)
 function calculateSimilarity(str1: string, str2: string): number {
@@ -250,15 +272,31 @@
   // Filter and sort organizations based on similarity
   const suggestedOrgs = useMemo(() => {
     if (!parsedName || !availableOrganizations) return [];
     
     return availableOrganizations
       .map(org => ({
         ...org,
         similarity: calculateSimilarity(org.name, parsedName)
       }))
-      .filter(org => org.similarity > 0.4) // Replace existing threshold
+      .filter(org => org.similarity >= 0.9) // Strict 90% threshold
  
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Vitest with React Testing Library`

- **shouldAutoPopulateExactMatch** — Verifies that exact matches are automatically populated into the form.
- **shouldDisplaySuggestionsForHighSimilarity** — Verifies that organizations with >= 90% similarity are suggested to the user.
- **shouldNotDisplaySuggestionsForLowSimilarity** *(edge case)* — Verifies the strict 90% similarity threshold, ensuring low-match organizations are not suggested.
- **shouldDisplayParsedDataAtTop** — Verifies that the parsed IP and NIP details are clearly displayed to the user before selection.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD governs the Organization Management System, which includes the organization selection and creation logic being modified by this ticket.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Describes the current Case Creation workflow where staff enters both parties (IP and NIP), which is the process being updated with new organization selection logic.
- [IDRE Case Workflow Documentation](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/229277697) — Defines the Initiating Party (IP) and Non-Initiating Party (NIP) roles that are central to the organization selection step in case creation.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: Needs to be updated to include the new exact-match suggestion logic, the 90% match threshold constraint, and email auto-population rules for organization selection.
- IDRE Worflow: The "Case Creation" step needs to be updated to reflect that party information is parsed from the Notice of Initiation and to detail the new organization selection constraints.

## AI Confidence Scores
Plan: 95%, Code: 85%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._