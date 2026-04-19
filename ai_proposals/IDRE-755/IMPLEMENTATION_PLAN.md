## IDRE-755: CTS Slowness and HTTP 500 Errors 

**Jira Ticket:** [IDRE-755](https://orchidsoftware.atlassian.net//browse/IDRE-755)

## Summary
This plan addresses the critical database connection pool exhaustion by increasing the pool limit via the `DATABASE_URL` environment variable. First, the implementation will verify the Prisma client singleton instantiation in `lib/database/client.ts`. Then, the connection limit in the `DATABASE_URL` will be increased from 5 to a more suitable number (e.g., 15). Finally, the change will be deployed and the application monitored to ensure the 500 errors and slowness are resolved.

## Implementation Plan

**Step 1: Investigate Prisma Client Instantiation and Configuration**  
The ticket identifies the root cause as database connection pool exhaustion. The `prisma/schema.prisma` file shows that the connection URL is sourced from the `DATABASE_URL` environment variable. First, review `lib/database/client.ts` to confirm how the Prisma client is instantiated and that a singleton pattern is being used. This file is described as handling "connection pooling limits for serverless environments" and is the most likely place to verify how the connection string is processed. Ensure that a new `PrismaClient` is not being created on every request, as this is a common cause of pool exhaustion.
Files: `lib/database/client.ts`, `prisma/schema.prisma`

**Step 2: Increase Database Connection Pool Limit**  
The core issue is the connection pool limit being set to 5. This is almost certainly configured within the `DATABASE_URL` environment variable (e.g., `mysql://.../?connection_limit=5`). Update this environment variable in your deployment settings (e.g., Vercel, AWS, `.env.production`) to increase the connection limit. A reasonable starting point would be to increase it to 15 or 20. This is a configuration change and does not require a code commit, but it is the primary fix for the issue.

**Step 3: Deploy and Monitor Application Performance**  
After deploying the environment variable change, closely monitor the application's error logs in PostHog. Specifically, look for a reduction and eventual elimination of the `PrismaClientKnownRequestError` related to connection pool timeouts. Also, observe the secondary issues mentioned in the ticket (CMS errors, session failures) to confirm they have subsided. Monitor database performance to ensure the increased connection count has not negatively impacted its stability.

**Risk Level:** MEDIUM — The change itself is a simple configuration update, but modifying database connection parameters in a production environment carries inherent risk. Increasing the connection limit might expose underlying performance issues or put additional strain on the database server if it's already near capacity. The chosen connection limit is an estimate and may need further tuning based on post-deployment monitoring.

**Deployment Notes:**
- The change to the `DATABASE_URL` environment variable will require an application restart or redeployment to take effect.
- Post-deployment monitoring of database connections, CPU utilization, and application error rates (via PostHog or other monitoring tools) is critical to ensure the new connection limit is stable and has resolved the issue without overloading the database.

## Proposed Code Changes

### `lib/database/client.ts` (modify)
The original implementation creates a new `PrismaClient` instance every time the module is loaded. In a development environment with hot-reloading, or in a serverless environment under certain conditions, this can lead to the creation of many instances, quickly exhausting the database's connection pool. This change implements the recommended singleton pattern for Prisma in a Next.js application by caching the client instance on the `global` object, ensuring only one instance is active, which is critical to resolving the connection pool exhaustion issue described in IDRE-755.
```typescript
--- a/lib/database/client.ts
+++ b/lib/database/client.ts
@@ -1,5 +1,20 @@
 import { PrismaClient } from '@prisma/client';
 
-const prisma = new PrismaClient();
+// PrismaClient is attached to the `global` object in development to prevent
+// exhausting the database connection pool with every hot-reload.
+// In production, a single instance is created.
+// This is a best practice for using Prisma with Next.js.
+// See: https://www.prisma.io/docs/guides/database/troubleshooting-orm/help-articles/nextjs-prisma-client-dev-practices
 
-export default prisma;
+declare global {
+  // allow global `var` declarations
+  // eslint-disable-next-line no-var
+  var prisma: PrismaClient | undefined;
+}
+
+const client = global.prisma || new PrismaClient();
+if (process.env.NODE_ENV !== 'production') {
+  global.prisma = client;
+}
+
+export default client;
```

**New Dependencies:**
- `None`

## Test Suggestions

Framework: `Jest`

- **shouldCreateNewInstanceIfNoneExistsOnGlobal** — Verifies that a new PrismaClient is created and cached on the global object when no instance exists, which is the expected behavior on application startup.
- **shouldReturnExistingInstanceIfOneExistsOnGlobal** — This is a regression test to confirm that subsequent requests for the Prisma client return the same singleton instance, directly validating the fix for the connection pool exhaustion bug.

## AI Confidence Scores
Plan: 90%, Code: 90%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._