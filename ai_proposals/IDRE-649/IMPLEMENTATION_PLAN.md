## IDRE-649: IP / NIP Review - Report & Actions exceed the width of the page

**Jira Ticket:** [IDRE-649](https://orchidsoftware.atlassian.net//browse/IDRE-649)

## Summary
This plan addresses the UI issue where the "IP / NIP Review" report content exceeds the page width. The fix involves modifying the `components/reports/daily-transactions-report.tsx` file to apply CSS styles to the report's table. Specifically, the table layout will be set to fixed, and the columns containing long text will be assigned specific widths with text wrapping enabled, resolving the horizontal overflow.

## Implementation Plan

**Step 1: Apply fixed layout to the report table**  
In the `DailyTransactionsReport` component, locate the main `<Table>` element. Apply a CSS class to enforce a fixed table layout, which will prevent columns from expanding based on content. This is the foundation for setting specific column widths. For example, using Tailwind CSS, add the `table-fixed` class.
Files: `components/reports/daily-transactions-report.tsx`

**Step 2: Set column widths and enable text wrapping**  
Identify the `<TableHead>` and `<TableCell>` elements for the columns that contain long text (e.g., the organization names shown in the screenshot, which likely correspond to the `disputeName` field). Add CSS classes to these elements to define their width and enable text wrapping. For example, use width utility classes (e.g., `w-1/3`) and a word-breaking class (e.g., `break-words`) to ensure the content wraps instead of overflowing. Also, assign a fixed, smaller width to the "Actions" column containing the buttons.
Files: `components/reports/daily-transactions-report.tsx`

**Risk Level:** MEDIUM — The primary risk is that `components/reports/daily-transactions-report.tsx` is not the correct file. The component's name and the data model found in the exploration report do not perfectly align with the screenshot of the "IP / NIP Review" page. If this assumption is wrong, the fix will be applied to the wrong report.

## Proposed Code Changes

### `components/reports/daily-transactions-report.tsx` (modify)
As per the implementation plan, this change addresses the horizontal overflow issue.
1.  The `<Table>` component is given `w-full table-fixed` classes. This forces the table to adhere to the specified column widths rather than expanding based on content.
2.  Specific fractional widths (e.g., `w-1/12`, `w-5/12`) are assigned to each `<TableHead>`, ensuring the columns are proportionally sized and collectively fill the table width.
3.  The `break-words` class is added to the `disputeName` `<TableCell>` to enable text wrapping for long organization names, preventing them from stretching the column and causing overflow.
```
--- a/components/reports/daily-transactions-report.tsx
+++ b/components/reports/daily-transactions-report.tsx
@@ -176,29 +176,29 @@
         </div>
       )}
       {transactions.length > 0 && (
-        <Table>
+        <Table className="w-full table-fixed">
           <TableHeader>
             <TableRow>
-              <TableHead>7-Digit ID</TableHead>
-              <TableHead>Dispute Name</TableHead>
-              <TableHead>Type</TableHead>
-              <TableHead className="text-right">Amount</TableHead>
-              <TableHead>Date</TableHead>
-              <TableHead>Actions</TableHead>
+              <TableHead className="w-1/12">7-Digit ID</TableHead>
+              <TableHead className="w-5/12">Dispute Name</TableHead>
+              <TableHead className="w-1/12">Type</TableHead>
+              <TableHead className="w-2/12 text-right">Amount</TableHead>
+              <TableHead className="w-2/12">Date</TableHead>
+              <TableHead className="w-1/12">Actions</TableHead>
             </TableRow>
           </TableHeader>
           <TableBody>
             {transactions.map((tx) => (
               <TableRow key={tx.sevenDigitId}>
                 <TableCell>{tx.sevenDigitId}</TableCell>
-                <TableCell>{tx.disputeName}</TableCell>
+                <TableCell className="break-words">{tx.disputeName}</TableCell>
                 <TableCell>{tx.type}</TableCell>
                 <TableCell className="text-right">
                   {new Intl.NumberFormat("en-US", {
                     style: "currency",
                     currency: "USD",
                   }).format(tx.amount)}
                 </TableCell>
                 <TableCell>
                   {formatDate(new Date(tx.occurredAt), "MM/dd/yyyy p")}
                 </TableCell>
                 <TableCell>
                   <Button
                     variant="outline"
                     size="sm"
                     onClick={() => window.open(`/dashboard/cases/${
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This Product Requirements Document (PRD) for the parent feature "Organization Management" explicitly states the requirement that all reports must be viewable without horizontal scrolling and that table content should wrap. This provides the developer with the specific business rule and design constraint they need to implement the fix.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This release overview confirms that the "IP/NIP Review" report is a key part of the "Organization Management" feature. It also contains screenshots that can serve as a visual reference for the developer to understand the context of the page they are fixing and what the final, corrected layout should look like in relation to other UI elements.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: Should be updated with new screenshots of the IP/NIP Review report to reflect the corrected layout after the fix is implemented.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: Any screenshots in this overview that show the defective report table should be replaced with images of the corrected UI.

## AI Confidence Scores
Plan: 40%, Code: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._