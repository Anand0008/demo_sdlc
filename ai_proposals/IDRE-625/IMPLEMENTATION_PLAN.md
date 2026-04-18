## IDRE-625: Generate List of Organization Records with NIP/IP Mismatches for Manual Review

**Jira Ticket:** [IDRE-625](https://orchidsoftware.atlassian.net//browse/IDRE-625)

## Summary
This plan outlines the creation of a new API endpoint to generate a list of cases with Initiating Party (IP) and Non-Initiating Party (NIP) mismatches. A new route, `app/api/reports/party-mismatches/route.ts`, will be created following the pattern of existing reports. The implementation will query all cases with their related party and organization data, apply logic to filter for records where the party's assigned organization differs from the case-level organization, and return a formatted JSON list as specified in the ticket for manual review.

## Implementation Plan

**Step 1: Create New API Route for Mismatch Report**  
Create a new API route file at `app/api/reports/party-mismatches/route.ts`. This file will contain a `GET` handler responsible for generating the report. The structure should be based on the existing report file `app/api/reports/outstanding-payments/route.ts`, including role-based access control to ensure only authorized users can access it.
Files: `app/api/reports/party-mismatches/route.ts`

**Step 2: Implement Prisma Query to Fetch Case Data**  
Within the `GET` handler, implement a Prisma query to fetch all cases. The query must include related data needed for the mismatch logic and the final report. Specifically, it should include: `dispute`, `initiatingParty` (with its related `user` and `organization`), `nonInitiatingParty` (with its related `user` and `organization`), `initiatingPartyOrganization`, and `nonInitiatingPartyOrganization`.
Files: `app/api/reports/party-mismatches/route.ts`

**Step 3: Implement Mismatch Identification Logic**  
After fetching the data, filter the results in the application code to identify the mismatches. Iterate through each case and check for two conditions:
1. `case.initiatingParty.organizationId !== case.initiatingPartyOrganizationId`
2. `case.nonInitiatingParty.organizationId !== case.nonInitiatingPartyOrganizationId`
If either condition is true, the case should be included in the final report.
Files: `app/api/reports/party-mismatches/route.ts`

**Step 4: Format and Return Mismatch Data**  
Format the filtered list of mismatched cases into the structure specified in the ticket. Each object in the response array should have the following keys: `Dispute`, `IP_Name`, `Organization_IP`, `NIP_Name`, `Organization_NIP`. Populate these fields using the data retrieved in the Prisma query. Return the final array as a JSON response.
Files: `app/api/reports/party-mismatches/route.ts`

**Risk Level:** LOW — This task involves creating a new, read-only API endpoint for internal reporting. It does not modify any data or affect user-facing functionality, making the risk of negative impact very low. The logic is self-contained within the new route.

## Proposed Code Changes

### `app/api/reports/party-mismatches/route.ts` (create)
This new file creates the API endpoint `GET /api/reports/party-mismatches` as specified in the implementation plan. It includes role-based access control to ensure only authorized users can generate the report. The Prisma query fetches all necessary case, party, and organization data. The code then filters these cases to find records where a party's actual organization differs from the one assigned at the case level, formats the results into the required structure, and returns them as a JSON response. Error handling and null-safe accessors are included for robustness.
```typescript
import { NextResponse } from "next/server";
import { prisma } from "@/lib/database";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth/options";
import { hasPermission } from "@/lib/auth/permissions";
import { UserPermission } from "@prisma/client";

/**
 * @swagger
 * /api/reports/party-mismatches:
 *   get:
 *     summary: Generate a list of cases with NIP/IP organization mismatches
 *     description: |
 *       Retrieves all cases and identifies records where the organization associated with the
 *       Initiating Party (IP) or Non-Initiating Party (NIP) does not match the organization
 *       assigned to that role at the case level. This report is used for manual review and correction.
 *       Requires VIEW_REPORTS permission.
 *     tags:
 *       - Reports
 *     responses:
 *       200:
 *         description: A JSON array of mismatched case records.
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 type: object
 *                 properties:
 *                   Dispute:
 *                     type: string
 *                     description: The dispute number.
 *                   IP_Name:
 *                     type: string
 *                     description: The name of the Initiating Party's user.
 *                   Organization_IP:
 *                     type: string
 *                     description: The name of the organization assigned to the IP role on the case.
 *                   NIP_Name:
 *                     type: string
 *                     description: The name of the Non-Initiating Party's user.
 *                   Organization_NIP:
 *                     type: string
 *                     description: The name of the organization assigned to the NIP role on the case.
 *       401:
 *         description: Unauthorized, user is not authenticated.
 *       403:
 *         description: Forbidden, user 
... (truncated — see full diff in files)
```

**New Dependencies:**
- `(none)`

## Test Suggestions

Framework: `Jest`

- **shouldReturnFormattedListOfMismatchesWhenTheyExist** — Verifies that the endpoint correctly identifies and returns a formatted list of all cases with IP/NIP organization mismatches when such cases exist.
- **shouldReturnEmptyArrayWhenNoMismatchesAreFound** *(edge case)* — Ensures the endpoint returns an empty list when the database contains no cases with party organization mismatches.
- **shouldReturn403ForbiddenForUnauthorizedUser** — Validates that the role-based access control correctly prevents unauthorized users from accessing the report.
- **shouldReturn500InternalServerErrorWhenDatabaseQueryFails** *(edge case)* — Tests the endpoint's error handling capability to ensure it fails gracefully if the database query throws an exception.
- **shouldHandleCasesWithMissingPartyOrOrganizationDataGracefully** *(edge case)* — Verifies that the filtering logic is robust and handles records with incomplete or null data without crashing, as per the implementation notes on "null-safe accessors".

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page defines the fundamental business roles of "Initiating Party" (IP) and "Non-Initiating Party" (NIP) within the dispute lifecycle. It explicitly states that the IP is the provider who files the dispute, which is a core business rule needed to identify a potential mismatch.
- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — As the primary Product Requirements Document for the Organization Management System, this page is the authoritative source for business rules, data models, and intended functionality defining how organizations and their roles (IP/NIP) are managed. The definition of a "mismatch" would be based on the rules specified in this document.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._