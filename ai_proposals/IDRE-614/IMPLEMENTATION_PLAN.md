## IDRE-614: User is not able to perform Detach from this hierarchy

**Jira Ticket:** [IDRE-614](https://orchidsoftware.atlassian.net//browse/IDRE-614)

## Summary
This plan addresses the bug where a user cannot detach an organization from its hierarchy. The root cause is likely a faulty pre-condition check in the corresponding server action that incorrectly assesses the organization's active cases or outstanding payments. The fix involves correcting this validation logic and adding comprehensive unit tests to ensure organizations can be detached under the proper conditions and prevent future regressions.

## Implementation Plan

**Step 1: Correct the pre-condition logic in the detach organization server action**  
Locate the server action responsible for detaching an organization (e.g., `detachFromHierarchy`). Inside this function, analyze the pre-condition checks that validate whether the organization can be detached. These checks likely query the database for associated active cases or unpaid invoices. The bug is probably in the `where` clause of these queries (e.g., checking for incorrect statuses). Modify the logic to correctly reflect the business rules for when an organization is eligible for detachment.
Files: `lib/actions/organization.ts`

**Step 2: Create a new test file for organization actions**  
Create a new test file `tests/actions/organization.test.ts` to house unit tests for organization-related server actions. This is necessary as no existing test file for this functionality was found in the provided context.
Files: `tests/actions/organization.test.ts`

**Step 3: Add unit tests to cover the detachment logic**  
Add unit tests to validate the fix. Create a test case for an organization that was previously blocked from detachment but should be allowed (e.g., it only has closed cases). Mock the database calls to simulate this scenario and assert that the action succeeds. Add a regression test for an organization that should be correctly blocked from detachment (e.g., has active cases or outstanding payments) and assert that the action fails with an appropriate error.
Files: `tests/actions/organization.test.ts`

**Risk Level:** LOW — The proposed change is a targeted fix to a specific business rule within a single server action. The risk of unintended side effects is low, especially as the fix will be validated by new unit tests covering both the success and failure scenarios for the detachment logic.

## Proposed Code Changes

### `lib/actions/organization.ts` (modify)
The original logic for checking active cases was too broad, counting all cases associated with an organization regardless of their status. This change refines the database query to exclude cases with terminal statuses (e.g., `CLOSED`, `RESOLVED`, `CANCELLED`), ensuring that only genuinely active cases block the detachment operation. This directly addresses the bug reported in the ticket.
```typescript
--- a/lib/actions/organization.ts
+++ b/lib/actions/organization.ts
@@ -1,5 +1,6 @@
 "use server";
 
+import { CaseStatus } from "@prisma/client";
 import { z } from "zod";
 import { prisma } from "@/lib/database";
 import { revalidatePath } from "next/cache";
@@ -25,6 +26,12 @@
           { initiatingPartyOrganizationId: organizationId },
           { nonInitiatingPartyOrganizationId: organizationId },
         ],
+        // FIX: Only count cases that are not in a terminal state. The previous
+        // logic counted all cases, incorrectly blocking detachment for
+        // organizations with only closed or resolved cases.
+        status: {
+          notIn: [CaseStatus.CLOSED, CaseStatus.RESOLVED, CaseStatus.CANCELLED],
+        },
       },
     });
```

### `tests/actions/organization.test.ts` (create)
To ensure the fix is robust and prevent future regressions, this new test file provides comprehensive unit test coverage for the `detachFromHierarchy` server action. It validates the corrected logic by testing the scenario where detachment succeeds (no active cases) and the scenario where it is correctly blocked (active cases present). It also covers essential edge cases, including authorization failures and unexpected database errors.
```typescript
import { detachFromHierarchy } from '@/lib/actions/organization';
import { prisma } from '@/lib/database';
import { getSession } from '@/lib/auth';
import { hasPermission } from '@/lib/auth/permissions';
import { CaseStatus } from '@prisma/client';
import { ActionResponse } from '@/lib/types';

// Mock dependencies
jest.mock('@/lib/database', () => ({
  prisma: {
    case: {
      count: jest.fn(),
    },
    organization: {
      update: jest.fn(),
    },
  },
}));

jest.mock('@/lib/auth', () => ({
  getSession: jest.fn(),
}));

jest.mock('@/lib/auth/permissions', () => ({
  hasPermission: jest.fn(),
}));

jest.mock('next/cache', () => ({
  revalidatePath: jest.fn(),
}));

const prismaMock = prisma as jest.Mocked<typeof prisma>;
const getSessionMock = getSession as jest.Mock;
const hasPermissionMock = hasPermission as jest.Mock;

describe('detachFromHierarchy action', () => {
  const organizationId = 'org_12345';

  beforeEach(() => {
    jest.clearAllMocks();
    // Default to an authorized admin user for most tests
    getSessionMock.mockResolvedValue({
      user: { role: 'admin' },
    });
    hasPermissionMock.mockReturnValue(true);
  });

  it('should successfully detach an organization with no active cases', async () => {
    // Arrange
    prismaMock.case.count.mockResolvedValue(0);
    prismaMock.organization.update.mockResolvedValue({ id: organizationId, parentId: null, name: 'Test Org', slug: 'test-org', type: 'HEALTH_PLAN', email: 'test@test.com', createdAt: new Date(), updatedAt: new Date() });

    // Act
    const result = await detachFromHierarchy(organizationId);

    // Assert
    expect(result.success).toBe(true);
    expect(result.message).toBe('Organization detached from hierarchy.');
    expect(prismaMock.case.count).toHaveBeenCalledWith({
      where: {
        OR: [
          { initiatingPartyOrganizationId: organizationId },
          { nonInitiatingPartyOrganizationId: organizationId },
        ],
        status: {
          notIn: [CaseSt
... (truncated — see full diff in files)
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldAllowDetachmentWhenOrganizationHasOnlyClosedCases** — This is the primary regression test. It ensures that an organization can be detached when its associated cases are not active, which was the core issue of the bug.
- **shouldPreventDetachmentWhenOrganizationHasActiveCases** — This test verifies that the original, correct behavior is preserved. It ensures the check for active cases still works and prevents detachment when it's not supposed to happen.
- **shouldThrowErrorWhenUserIsNotAuthenticated** *(edge case)* — This test covers the security aspect, ensuring that only authenticated users can perform the action.
- **shouldThrowErrorOnDatabaseFailureDuringCaseCheck** *(edge case)* — This test ensures the action is resilient and handles unexpected database failures gracefully.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This is the Product Requirements Document (PRD) for the feature area in question. It should contain the definitive business rules, user stories, and acceptance criteria for how the 'detach from hierarchy' functionality is designed to work.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System

## AI Confidence Scores
Plan: 80%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._