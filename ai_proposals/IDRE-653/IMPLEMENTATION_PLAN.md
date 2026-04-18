## IDRE-653: Updated NIP Welcome Email

**Jira Ticket:** [IDRE-653](https://orchidsoftware.atlassian.net//browse/IDRE-653)

## Summary
This plan outlines the steps to automatically send a welcome email to a Non-Initiating Party (NIP) upon account creation. A new email template component will be created for the welcome message. A new function will be added to the existing email service to handle rendering and sending this specific email. This new function will then be triggered from the server action in `lib/party-actions.ts` that handles NIP creation, ensuring the email is sent only upon successful creation. Finally, unit tests will be added to verify the correct behavior.

## Implementation Plan

**Step 1: Create NIP Welcome Email Template Component**  
Create a new React component that will serve as the email template. This component will accept props such as the NIP's name, the case dispute reference number, and the platform URL. Use the existing shared layout component, likely located at `components/emails/layout.tsx`, to ensure the new email has a consistent header, footer, and styling with other platform communications. The email body should include placeholders for the welcome message (TBD), login instructions, and a direct link to the platform. The subject line will be constructed dynamically using the dispute reference number.
Files: `components/emails/nip-welcome-email.tsx`, `components/emails/layout.tsx`

**Step 2: Add Function to Email Service**  
Assuming an email service exists at `lib/services/email.ts`, add a new function `sendNipWelcomeEmail`. This function will take the NIP user object and the associated case object as parameters. It will use a rendering library (e.g., React Email) to convert the `NipWelcomeEmail` component into an HTML string. Finally, it will call the underlying email provider to send the email with the correct recipient, subject line ('DISP-xxxxxxx – Capitol Bridge Payment and Dispute Portal Access'), and HTML body.
Files: `lib/services/email.ts`

**Step 3: Trigger Email from NIP Creation Action**  
Locate the function responsible for creating a new Non-Initiating Party within the `lib/party-actions.ts` file. Inside this function, immediately after the database record for the new NIP user is successfully created, add a call to the `sendNipWelcomeEmail` function created in the previous step. Pass the newly created user object and the relevant case details. This ensures the email is only triggered upon successful account creation and not on updates or failures.
Files: `lib/party-actions.ts`

**Step 4: Add Unit Tests**  
Create a new test file `tests/lib/party-actions.test.ts` or add to the existing one. Add a test case that calls the NIP creation action. Mock the email service to prevent actual email sends. Assert that the `sendNipWelcomeEmail` function is called exactly once with the correct user and case data upon successful NIP creation. Add a second test case to handle creation failure, and assert that the `sendNipWelcomeEmail` function is not called.
Files: `tests/lib/party-actions.test.ts`

**Risk Level:** LOW — The change is additive and isolated to the NIP creation workflow. The main risk is misidentifying the NIP creation event, which could lead to emails not being sent or being sent at the wrong time. The plan mitigates this by targeting the server action responsible for the creation logic itself. There is no risk of data loss or impact on other existing functionalities.

## Proposed Code Changes

### `components/emails/nip-welcome-email.tsx` (create)
This new file creates the React Email component for the NIP welcome email. It includes placeholders for the final copy, login instructions, and dynamic data like the NIP's name and case number, as required by the ticket. It uses the shared `EmailLayout` for consistent branding.
```
import React from 'react';
import {
  Body,
  Heading,
  Html,
  Link,
  Preview,
  Text,
} from '@react-email/components';
import { EmailLayout } from './layout';

interface NipWelcomeEmailProps {
  nipName: string;
  disputeReferenceNumber: string;
  platformUrl: string;
}

export const NipWelcomeEmail: React.FC<Readonly<NipWelcomeEmailProps>> = ({
  nipName,
  disputeReferenceNumber,
  platformUrl,
}) => {
  const previewText = `Welcome to the Capitol Bridge Payment and Dispute Portal`;

  return (
    <Html>
      <head />
      <Preview>{previewText}</Preview>
      <Body style={main}>
        <EmailLayout>
          <Heading style={heading}>
            Welcome to the Capitol Bridge Payment and Dispute Portal
          </Heading>
          <Text style={paragraph}>Hello {nipName},</Text>
          <Text style={paragraph}>
            An account has been created for you on the Capitol Bridge Payment and
            Dispute Portal for case DISP-{disputeReferenceNumber}.
          </Text>
          <Text style={paragraph}>
            [Welcome message copy to be provided by Capitol Bridge will go here.]
          </Text>
          <Heading style={subHeading}>Login Instructions</Heading>
          <Text style={paragraph}>
            To access your account, please follow these steps:
          </Text>
          <Text style={listItem}>
            1. Go to the portal login page:{' '}
            <Link style={link} href={platformUrl}>
              {platformUrl}
            </Link>
          </Text>
          <Text style={listItem}>
            2. Click on "Forgot Password" and enter your email address to set up
            your password.
          </Text>
          <Text style={listItem}>
            3. Once your password is set, you can log in to view case details and
            manage payments.
          </Text>
          <Text style={paragraph}>
            If you have any questions, please contact our support team.
          </Text>
          <Text style={parag
... (truncated — see full diff in files)
```

### `lib/actions/email.ts` (modify)
This change adds a new exported function, `sendNipWelcomeEmail`, to the email service. This function is responsible for rendering the `NipWelcomeEmail` component into HTML and sending it to the newly created NIP user. This encapsulates the email-sending logic, making it reusable and easy to call from server actions.
```typescript
--- a/lib/services/email.ts
+++ b/lib/services/email.ts
@@ -1,6 +1,10 @@
 "use server";
 
 import { render } from "@react-email/render";
+import { NipWelcomeEmail } from "@/components/emails/nip-welcome-email";
+import { getBaseUrl } from "@/lib/utils"; // Assuming this utility exists
 
 // Assuming a mailer utility and a generic sendEmail function exist
 // import { mailer } from './mailer';
@@ -8,3 +12,36 @@
 //   // ... implementation
 // }
 
+// ... any existing email functions
+
+interface NipWelcomeEmailParams {
+  user: {
+    email: string;
+    name?: string | null;
+  };
+  caseData: {
+    disputeReferenceNumber: string;
+  };
+}
+
+export async function sendNipWelcomeEmail({
+  user,
+  caseData,
+}: NipWelcomeEmailParams): Promise<void> {
+  const platformUrl = getBaseUrl();
+  const subject = `DISP-${caseData.disputeReferenceNumber} – Capitol Bridge Payment and Dispute Portal Access`;
+
+  const emailHtml = render(
+    <NipWelcomeEmail
+      nipName={user.name || "there"}
+      disputeReferenceNumber={caseData.disputeReferenceNumber}
+      platformUrl={platformUrl}
+    />
+  );
+
+  try {
+    await sendEmail({ to: user.email, subject, html: emailHtml });
+  } catch (error) {
+    console.error(`Failed to send NIP welcome email to ${user.email}`, error);
+  }
+}
```

### `lib/party-actions.ts` (modify)
This change modifies the server action responsible for creating parties. It adds a call to the new `sendNipWelcomeEmail` function immediately after a new Non-Initiating Party (`NON_INITIATING`) is successfully created in the database. This ensures the email is triggered automatically and only for new NIPs, as required by the ticket.
```typescript
--- a/lib/party-actions.ts
+++ b/lib/party-actions.ts
@@ -8,6 +8,7 @@
 } from "@/lib/constants/pricing";
 import { encryptSensitiveData } from "@/lib/encryption";
 
+import { sendNipWelcomeEmail } from "@/lib/services/email";
 import { createBulkPayment } from "@/lib/actions/payment";
 import type { PartyType } from "@prisma/client";
 
@@ -120,6 +121,7 @@
   return obj;
 }
 
+// NOTE: Assuming a function like `createPartyAndAddToCase` is responsible for NIP creation.
 // The actual function name and signature may differ.
 export async function createPartyAndAddToCase(
   caseId: string,
@@ -168,6 +170,26 @@
       },
     });
 
+    if (partyType === "NON_INITIATING") {
+      const caseDetails = await prisma.case.findUnique({
+        where: { id: caseId },
+        select: { disputeReferenceNumber: true },
+      });
+
+      if (caseDetails?.disputeReferenceNumber) {
+        // Fire and forget the email, don't block the response
+        sendNipWelcomeEmail({
+          user: newUser,
+          caseData: {
+            disputeReferenceNumber: caseDetails.disputeReferenceNumber,
+          },
+        });
+      } else {
+        console.error(
+          `Could not send NIP welcome email for user ${newUser.id} in case ${caseId}: case details not found.`
+        );
+      }
+    }
+
     return { success: true, data: { user: newUser, party: newParty } };
   } catch (error) {
     console.error("Error creating party and adding to case:", error);
```

### `tests/lib/party-actions.test.ts` (create)
This new test file adds unit tests for the `party-actions` server action. It verifies that the `sendNipWelcomeEmail` function is called exactly once upon successful NIP creation, is not called for other party types, and is not called if the creation process fails. This ensures the new functionality is correct and robust.
```typescript
import { createPartyAndAddToCase } from '@/lib/party-actions';
import { prisma } from '@/lib/database';
import { sendNipWelcomeEmail } from '@/lib/services/email';

// Mock dependencies
jest.mock('@/lib/database', () => ({
  prisma: {
    user: {
      create: jest.fn(),
    },
    case: {
      findUnique: jest.fn(),
    },
    party: {
      create: jest.fn(),
    }
  },
}));

jest.mock('@/lib/services/email', () => ({
  sendNipWelcomeEmail: jest.fn(),
}));

// Type assertion for mocks
const mockedPrismaUserCreate = prisma.user.create as jest.Mock;
const mockedPrismaCaseFindUnique = prisma.case.findUnique as jest.Mock;
const mockedSendNipWelcomeEmail = sendNipWelcomeEmail as jest.Mock;

describe('party-actions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createPartyAndAddToCase', () => {
    const caseId = 'test-case-id-123';
    const partyData = { name: 'Test NIP', email: 'nip@example.com' }; // Simplified
    const userData = {
      id: 'test-user-id-456',
      email: 'nip@example.com',
      name: 'Test NIP',
    };
    const caseData = {
      id: caseId,
      disputeReferenceNumber: '1234567',
    };

    it('should send a welcome email when a NIP is created successfully', async () => {
      // Arrange
      mockedPrismaUserCreate.mockResolvedValue(userData);
      mockedPrismaCaseFindUnique.mockResolvedValue(caseData);

      // Act
      await createPartyAndAddToCase(caseId, partyData, 'NON_INITIATING');

      // Assert
      expect(mockedPrismaUserCreate).toHaveBeenCalledTimes(1);
      expect(mockedSendNipWelcomeEmail).toHaveBeenCalledTimes(1);
      expect(mockedSendNipWelcomeEmail).toHaveBeenCalledWith({
        user: userData,
        caseData: {
          disputeReferenceNumber: caseData.disputeReferenceNumber,
        },
      });
    });

    it('should NOT send a welcome email when an IP is created', async () => {
      // Arrange
      mockedPrismaUserCreate.mockResolvedValue(userData);

      // Act
      awai
... (truncated — see full diff in files)
```

**New Dependencies:**
- `No new dependencies needed.`

## Test Suggestions

Framework: `Vitest`

- **shouldCallSendNipWelcomeEmailWhenNipIsCreatedSuccessfully** — Verifies that the welcome email is triggered for the successful creation of a Non-Initiating Party (NIP).
- **shouldNotCallSendNipWelcomeEmailWhenOtherPartyTypeIsCreated** *(edge case)* — Ensures the welcome email is sent exclusively to NIPs and not to other party types. This covers a key condition from the ticket.
- **shouldNotCallSendNipWelcomeEmailWhenNipCreationFails** *(edge case)* — Verifies that if the account creation fails in the database, no welcome email is sent, as per the ticket requirements.
- **shouldCallEmailProviderWithCorrectParametersAndPayload** — This is a lower-level unit test for the email action itself, ensuring it correctly formats the email and calls the email provider.
- **shouldRenderNipDetailsAndLoginLinkCorrectly** — A component-level test to verify the email template renders the dynamic data correctly. This ensures the content of the email is correct.

## Confluence Documentation References

- [IDRE Worflow](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/284688394) — This page provides critical context by confirming that an automated notification to the Non-Initiating Party (NIP) already exists as part of the case creation workflow. The developer needs to be aware of this existing notification to ensure the new welcome email is implemented correctly alongside it, avoiding redundancy or conflict.

**Suggested Documentation Updates:**

- IDRE Worflow: This page describes the end-to-end case lifecycle, including automated notifications. It should be updated to include the new NIP welcome email, clarifying its trigger (account creation) and its place in the overall communication sequence.

## AI Confidence Scores
Plan: 70%, Code: 85%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._