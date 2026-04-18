## IDRE-754: Improve duplicate organization scanning logic to use exact name

**Jira Ticket:** [IDRE-754](https://orchidsoftware.atlassian.net//browse/IDRE-754)

## Summary
This plan addresses the incorrect organization merge suggestions by modifying the organization search logic. The core change is to update the Prisma query in `app/api/organizations/search/route.ts` from a fuzzy text search to an exact, case-insensitive name match. A new test file will be created to validate that the new logic correctly returns only exact matches, preventing incorrect merge suggestions.

## Implementation Plan

**Step 1: Update organization search query to use exact match**  
In the GET handler of this route, locate the Prisma query that searches for organizations by name. The current implementation likely uses a fuzzy-matching condition like "contains". Modify this query to perform an exact, case-insensitive match. The Prisma query condition should be changed to use `{ equals: query, mode: "insensitive" }` on the organization name field.
Files: `app/api/organizations/search/route.ts`

**Step 2: Add unit tests for exact name matching**  
Create a new test file to verify the updated search logic. Add test cases that ensure the endpoint only returns organizations with an exact name match (case-insensitive). For example, a search for "Acme Inc" should return "Acme Inc" and "acme inc", but not "Acme Incorporated". This validates that the fuzzy matching has been removed.
Files: `tests/app/api/organizations/search/route.test.ts`

**Risk Level:** LOW — The change is confined to a single API endpoint and narrows the search criteria, which is the desired behavior. This reduces the risk of incorrect merge suggestions. There is a minor risk that some UI feature relied on the fuzzy search for a typeahead-style search, but based on the ticket, the primary use is for duplicate detection where precision is paramount.

## Proposed Code Changes

### `app/api/organizations/search/route.ts` (modify)
This change modifies the Prisma query to use `equals` instead of `contains` for the organization name search. This aligns with the ticket's requirement to move from a fuzzy text search to an exact match, preventing incorrect duplicate organization suggestions. The `mode: 'insensitive'` option is retained to ensure the match is case-insensitive.
```typescript
--- a/app/api/organizations/search/route.ts
+++ b/app/api/organizations/search/route.ts
@@ -21,8 +21,8 @@
   const organizations = await prisma.organization.findMany({
     where: {
       name: {
-        contains: query,
+        equals: query,
         mode: "insensitive",
       },
     },
```

### `tests/app/api/organizations/search/route.test.ts` (create)
This new test file provides unit test coverage for the organization search API endpoint. It verifies that the endpoint correctly requires authentication, handles missing query parameters, and most importantly, constructs a Prisma query for an exact, case-insensitive name match. This ensures the fix for IDRE-754 is validated and prevents future regressions.
```typescript
import { GET } from "@/app/api/organizations/search/route";
import { prisma } from "@/lib/database";
import { getCurrentSession } from "@/lib/auth/utils";
import { NextRequest } from "next/server";
import { Organization } from "@prisma/client";

// Mock dependencies
jest.mock("@/lib/auth/utils");
jest.mock("@/lib/database", () => ({
  prisma: {
    organization: {
      findMany: jest.fn(),
    },
  },
}));

const mockGetCurrentSession = getCurrentSession as jest.Mock;
const mockPrismaOrganizationFindMany = prisma.organization.findMany as jest.Mock;

describe("GET /api/organizations/search", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return 401 if user is not authenticated", async () => {
    mockGetCurrentSession.mockResolvedValue(null);
    const req = new NextRequest("http://localhost/api/organizations/search?q=test");
    const response = await GET(req);
    expect(response.status).toBe(401);
    const body = await response.json();
    expect(body).toEqual({ error: "Unauthorized" });
  });

  it("should return 400 if query parameter 'q' is missing", async () => {
    mockGetCurrentSession.mockResolvedValue({ user: { id: "user-1" } });
    const req = new NextRequest("http://localhost/api/organizations/search");
    const response = await GET(req);
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body).toEqual({ error: "Query parameter 'q' is required" });
  });

  it("should return organizations with an exact, case-insensitive name match", async () => {
    mockGetCurrentSession.mockResolvedValue({ user: { id: "user-1" } });

    const mockOrgs: Partial<Organization>[] = [
      { id: "org-1", name: "Exact Match Corp" },
    ];
    mockPrismaOrganizationFindMany.mockResolvedValue(mockOrgs);

    const req = new NextRequest("http://localhost/api/organizations/search?q=Exact%20Match%20Corp");
    const response = await GET(req);
    const body = await response.json();

    expect(response.sta
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldReturnOrganizationsWithExactCaseInsensitiveNameMatch** — This test validates the primary success path, ensuring the API correctly queries the database for an exact, case-insensitive name match and returns the found organizations.
- **shouldNotReturnOrganizationsWithPartialNameMatch** *(edge case)* — This is a regression test to confirm that the bug causing partial matches (e.g., searching for "Test" and finding "TestCo") is fixed. It ensures the query uses "equals" and not "contains".
- **shouldReturn400ErrorWhenNameQueryParamIsMissing** *(edge case)* — This test covers the error handling case where a required query parameter is missing from the request.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the feature being modified. It explicitly states that the original design for duplicate detection uses a "fuzzy string-matching algorithm on the organization name". This is the core business rule that the ticket is changing.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides a high-level overview of the Organization Management feature, confirming that the system "automatically suggests potential duplicates" for administrators to review and merge. This is relevant context for understanding the user-facing part of the feature being changed.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._