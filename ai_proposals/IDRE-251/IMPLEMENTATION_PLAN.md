## IDRE-251: Robust Organization Merge Tools

**Jira Ticket:** [IDRE-251](https://orchidsoftware.atlassian.net//browse/IDRE-251)

## Summary
Implement robust organization merge tools by adding data normalization, a 3-gate matching algorithm, and a server action to merge duplicates into a 1:N parent-child relationship while enforcing domain constraints.

## Implementation Plan

**Step 1: Implement Data Normalization Rules**  
Add data normalization utility functions: `normalizeOrgName` (lowercases, removes spaces/punctuation, and strips common suffixes like 'inc', 'llc', 'corp'), `normalizeEmailDomain` (extracts string after '@' and lowercases), and `normalizeEmailLocalPart` (extracts string before '@' and removes non-alphanumeric characters like dots).
Files: `lib/actions/admin.ts`

**Step 2: Implement the 3-Gate Matching Algorithm**  
Create an `evaluateOrganizationMatch(orgA, orgB)` function implementing the 3-gate algorithm. Gate 1: Exact domain match (returns DO_NOT_MERGE if different). Gate 2: Fuzzy name match (>85% similarity using Levenshtein distance). Gate 3: Sanitized local part match. Implement the QA matrix logic to return `SUGGEST_MERGE`, `FLAG_FOR_REVIEW`, or `DO_NOT_MERGE`.
Files: `lib/actions/admin.ts`

**Step 3: Create the Organization Merge Server Action**  
Implement a `mergeOrganizations(parentOrgId, childOrgId, forceMerge = false)` server action. Fetch both organizations and run `evaluateOrganizationMatch`. If the result is `DO_NOT_MERGE` and `!forceMerge`, return a warning payload (e.g., `{ warning: 'Merging organizations with different domains is not recommended.' }`). If proceeding, update the child organization to set `parentId = parentOrgId`, establishing the 1:N relationship while retaining the child's unique email address.
Files: `lib/actions/admin.ts`

**Risk Level:** LOW — The changes are isolated to new admin server actions and utility functions. They do not modify existing organization creation flows, minimizing the risk of breaking core functionality.

**Deployment Notes:**
- Ensure that any existing admin UI for organizations is updated to handle the new warning response from the merge action.

## Proposed Code Changes

### `lib/actions/admin.ts` (modify)
Added data normalization functions, the 3-gate matching algorithm, and the `mergeOrganizations` server action to `lib/actions/admin.ts` as requested in the implementation plan. The matching algorithm correctly implements the QA matrix logic, and the server action enforces the domain constraint unless `forceMerge` is true.
```typescript
@@ -55540,0 +55541,118 @@
+
+// --- Organization Merge Tools ---
+
+function levenshteinDistance(a: string, b: string): number {
+  const matrix = [];
+  for (let i = 0; i <= b.length; i++) {
+    matrix[i] = [i];
+  }
+  for (let j = 0; j <= a.length; j++) {
+    matrix[0][j] = j;
+  }
+  for (let i = 1; i <= b.length; i++) {
+    for (let j = 1; j <= a.length; j++) {
+      if (b.charAt(i - 1) === a.charAt(j - 1)) {
+        matrix[i][j] = matrix[i - 1][j - 1];
+      } else {
+        matrix[i][j] = Math.min(
+          matrix[i - 1][j - 1] + 1,
+          Math.min(matrix[i][j - 1] + 1, matrix[i - 1][j] + 1)
+        );
+      }
+    }
+  }
+  return matrix[b.length][a.length];
+}
+
+function calculateSimilarity(a: string, b: string): number {
+  if (a.length === 0 && b.length === 0) return 1;
+  const distance = levenshteinDistance(a, b);
+  const maxLength = Math.max(a.length, b.length);
+  return (maxLength - distance) / maxLength;
+}
+
+export function normalizeOrgName(name: string): string {
+  if (!name) return "";
+  let normalized = name.toLowerCase();
+  // remove punctuation and spaces
+  normalized = normalized.replace(/[^a-z0-9]/g, "");
+  // remove common suffixes
+  normalized = normalized.replace(/(inc|llc|corp|incorporated|corporation|company|co)$/, "");
+  return normalized;
+}
+
+export function normalizeEmailDomain(email: string): string {
+  if (!email || !email.includes("@")) return "";
+  return email.split("@")[1].toLowerCase();
+}
+
+export function normalizeEmailLocalPart(email: string): string {
+  if (!email || !email.includes("@")) return "";
+  let localPart = email.split("@")[0].toLowerCase();
+  // remove non-alphanumeric characters like dots
+  return localPart.replace(/[^a-z0-9]/g, "");
+}
+
+export type MatchResult = "SUGGEST_MERGE" | "FLAG_FOR_REVIEW" | "DO_NOT_MERGE";
+
+export function evaluateOrganizationMatch(
+  orgA: { name: string; email: string },
+  orgB: { name: string; email: string }
+): MatchResult {
+  const domain
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Vitest`

- **shouldNormalizeOrganizationNameCorrectly** — Verifies that organization names are correctly normalized for fuzzy matching
- **shouldReturnDoNotMergeWhenDomainsMismatch** *(edge case)* — Verifies the Hard Gate (Domain Check) correctly rejects merges for different domains regardless of name match
- **shouldSuggestMergeForFuzzyNameMatchAndExactEmail** — Verifies the Soft Gate (Name Similarity) correctly identifies typos and suggests a merge
- **shouldSuggestMergeForDotVarianceInEmail** *(edge case)* — Verifies the Local Part Gate correctly ignores dots when comparing email local parts
- **shouldFlagForReviewWhenLocalPartsDiffer** — Verifies that different users at the same organization are flagged for review rather than automatically suggested for merge
- **shouldRejectMergeWhenDomainsDifferUnlessForceMergeIsTrue** *(edge case)* — Verifies the critical constraint that the server action prevents merging different domains unless explicitly forced
- **shouldAllowMergeWithDifferentDomainsIfForceMergeIsTrue** *(edge case)* — Verifies the exception to the critical constraint where a user manually forces the merge of organizations with different domains

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._