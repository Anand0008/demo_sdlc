## IDRE-322: Report: IDRE Payouts

**Jira Ticket:** [IDRE-322](https://orchidsoftware.atlassian.net//browse/IDRE-322)

## Summary
Create a standalone script to manually pull a report of all completed IDRE payouts to Halo, VeraTru, and Capitol Bridge, outputting the results to a CSV format.

## Implementation Plan

**Step 1: Create manual data pull script**  
Create a new standalone script file `scripts/pull-idre-payouts.ts` to handle the manual data pull. Import and initialize the Prisma client to establish a database connection.
Files: `scripts/pull-idre-payouts.ts`

**Step 2: Implement database query for payouts**  
Implement a Prisma `$queryRaw` SQL query to retrieve the required data. Join the `payment` (p) table with `case_payment_allocation` (cpa) on `p.id = cpa.paymentId`, and join `case` (c) on `cpa.caseId = c.id`. Select the Payee by coalescing `JSON_UNQUOTE(JSON_EXTRACT(p.bankingSnapshot, '$.accountHolderName'))` and `p.recipientName`. Select `c.disputeReferenceNumber` as the Dispute ID, and format the earliest available completion timestamp (`processedAt`, `paidAt`, `updatedAt`, or `createdAt`) as the Date Payment Completed.
Files: `scripts/pull-idre-payouts.ts`

**Step 3: Apply filters and format CSV output**  
Add WHERE clauses to the SQL query to filter for `p.direction = 'OUTGOING'` and `p.status = 'COMPLETED'`. Add a filter to ensure the Payee matches 'halo', 'veratru', or 'capitol bridge' (using LOWER() for case-insensitivity). Finally, add logic in the script to iterate over the query results, format them as a CSV string, and output the result to the console or write it to a local `.csv` file.
Files: `scripts/pull-idre-payouts.ts`

**Risk Level:** LOW — The implementation consists of a single, standalone script for a manual data pull. It does not modify any existing application code, API routes, or database schemas, resulting in near-zero risk to the production system.

**Deployment Notes:**
- The script will need to be executed manually in an environment with database access (e.g., via a secure shell or task runner) to generate the report.

## Proposed Code Changes

### `scripts/pull-idre-payouts.ts` (create)
Creates a standalone script to manually pull the IDRE payouts report as requested in the ticket, since the in-system report is not needed yet. The script queries the database for completed outgoing payments to the specified payees, formats the results as a CSV, and writes it to the local filesystem.
```typescript
import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';

const prisma = new PrismaClient();

async function main() {
  console.log('Pulling IDRE payouts report...');

  const query = `
    SELECT 
      COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.bankingSnapshot, '$.accountHolderName')), p.recipientName) AS Payee,
      c.disputeReferenceNumber AS DisputeID,
      COALESCE(p.processedAt, p.paidAt, p.updatedAt, p.createdAt) AS DatePaymentCompleted
    FROM \`payment\` p
    JOIN \`case_payment_allocation\` cpa ON p.id = cpa.paymentId
    JOIN \`case\` c ON cpa.caseId = c.id
    WHERE p.direction = 'OUTGOING' 
      AND p.status = 'COMPLETED'
      AND LOWER(COALESCE(JSON_UNQUOTE(JSON_EXTRACT(p.bankingSnapshot, '$.accountHolderName')), p.recipientName)) IN ('halo', 'veratru', 'capitol bridge')
  `;

  try {
    const results = await prisma.$queryRawUnsafe<any[]>(query);

    if (!results || results.length === 0) {
      console.log('No payouts found matching the criteria.');
      return;
    }

    // Format as CSV
    const headers = ['Payee', 'Dispute ID', 'Date Payment Completed'];
    const csvRows = [headers.join(',')];

    for (const row of results) {
      const payee = `"${String(row.Payee || '').replace(/"/g, '""')}"`;
      const disputeId = `"${String(row.DisputeID || '').replace(/"/g, '""')}"`;
      
      // Format date
      let dateStr = '""';
      if (row.DatePaymentCompleted) {
        const d = new Date(row.DatePaymentCompleted);
        dateStr = `"${d.toISOString()}"`;
      }

      csvRows.push([payee, disputeId, dateStr].join(','));
    }

    const csvContent = csvRows.join('\n');
    const outputPath = path.join(process.cwd(), 'idre-payouts-report.csv');
    
    fs.writeFileSync(outputPath, csvContent);
    console.log(`Report successfully generated at: ${outputPath}`);
    console.log(`Total records: ${results.length}`);

  } catch (error) {
    console.error('Error pulling report:', error);
  } fi
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Jest`

- **should fetch completed payouts and write to CSV** — Verifies that the script successfully fetches completed payouts for the specified payees and writes them to a CSV file.
- **should handle empty database results gracefully** *(edge case)* — Ensures the script handles the scenario where no payouts match the criteria without crashing.
- **should log an error and abort if the database query fails** *(edge case)* — Verifies that database errors are handled gracefully and do not result in partial or corrupted file writes.
- **should correctly format dates and handle missing dispute IDs in CSV output** — Tests the data transformation logic to ensure CSV columns align correctly and dates are formatted properly.

## Confluence Documentation References

- [Case Balance Report](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/308936719) — Provides the database schema and SQL join structure for cases and payments, which is necessary to extract the Dispute ID and Payment Date for the requested report.
- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — Confirms that Capitol Bridge is the platform manager (one of the requested payees) and identifies that the Dispute ID is stored as the dispute reference number (DISP-XXXXXXX).
- [Release Notes - IDRE - v1.2.7 - Dec 11 17:41](https://orchidsoftware.atlassian.net/wiki/spaces/SD/pages/218529804) — Indicates that a recent database change (IDRE-336) created specific 'IDRE Payouts' logic or records, which is the exact data target for this report.

## AI Confidence Scores
Plan: 95%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._