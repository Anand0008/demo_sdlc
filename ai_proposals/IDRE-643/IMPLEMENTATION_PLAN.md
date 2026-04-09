## IDRE-643: Refine Organization Combine

**Jira Ticket:** [IDRE-643](https://orchidsoftware.atlassian.net//browse/IDRE-643)

## Summary
Implement a hybrid organization merge tool on the company tab, featuring an automated suggestion engine for finding duplicates and a manual safety check modal that warns users if email domains do not match before merging.

## Proposed Code Changes

### `components/organizations/merge-organization-modal.tsx` (create)
Creates the safety check modal as requested by the ticket, warning users if the primary email of the source organization does not match any emails or domains associated with the target organization.
```
"use client";

import React from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export interface Organization {
  id: string;
  name: string;
  primaryEmail?: string | null;
  emailDomains?: string[];
}

interface MergeOrganizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  sourceOrg: Organization | null;
  targetOrg: Organization | null;
  isLoading?: boolean;
}

export function MergeOrganizationModal({
  isOpen,
  onClose,
  onConfirm,
  sourceOrg,
  targetOrg,
  isLoading = false,
}: MergeOrganizationModalProps) {
  if (!sourceOrg || !targetOrg) return null;

  const sourceEmail = sourceOrg.primaryEmail || "";
  const sourceDomain = sourceEmail.includes("@") ? sourceEmail.split("@")[1] : "";
  
  const targetEmails = [targetOrg.primaryEmail, ...(targetOrg.emailDomains || [])].filter(Boolean) as string[];
  const targetDomains = targetEmails.map(e => e.includes("@") ? e.split("@")[1] : e);

  const hasMismatch = sourceEmail && targetEmails.length > 0 && !targetEmails.includes(sourceEmail) && (!sourceDomain || !targetDomains.includes(sourceDomain));

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            Security & Data Mismatch
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <p>
            You are merging <strong>{sourceOrg.name}</strong> with <strong>{targetOrg.name}</strong>.
          </p>

          {hasMismatch && (
            <div className="rounded-md bg-destructive/10 p-4 text-sm text-destructive">
              <strong>Warning:</strong> The primary email for {sourceOrg.name} (<strong>{sourceEmail}
... (truncated — see full diff in files)
```

### `components/organizations/organization-merge-tool.tsx` (create)
Implements the hybrid approach requested by the ticket, providing an automated suggestion engine that identifies duplicate organizations based on identical/similar names and associated email domains, and integrates the manual safety check modal.
```
"use client";

import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { MergeOrganizationModal, type Organization } from "./merge-organization-modal";

interface OrganizationMergeToolProps {
  organizations: Organization[];
  onMerge: (sourceId: string, targetId: string) => Promise<void>;
}

export function OrganizationMergeTool({ organizations, onMerge }: OrganizationMergeToolProps) {
  const [suggestions, setSuggestions] = useState<Array<{ source: Organization; target: Organization }>>([]);
  const [selectedMerge, setSelectedMerge] = useState<{ source: Organization; target: Organization } | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isMerging, setIsMerging] = useState(false);

  useEffect(() => {
    // Automated Suggestion Engine: Find orgs with similar names or matching email domains
    const newSuggestions: Array<{ source: Organization; target: Organization }> = [];
    
    for (let i = 0; i < organizations.length; i++) {
      for (let j = i + 1; j < organizations.length; j++) {
        const orgA = organizations[i];
        const orgB = organizations[j];
        
        const nameMatch = orgA.name.toLowerCase() === orgB.name.toLowerCase() || 
                          orgA.name.toLowerCase().includes(orgB.name.toLowerCase()) ||
                          orgB.name.toLowerCase().includes(orgA.name.toLowerCase());
                          
        const domainA = orgA.primaryEmail?.includes("@") ? orgA.primaryEmail.split("@")[1] : null;
        const domainB = orgB.primaryEmail?.includes("@") ? orgB.primaryEmail.split("@")[1] : null;
        const domainMatch = domainA && domainB && domainA === domainB;
        
        if (nameMatch || domainMatch) {
          newSuggestions.push({ source: orgA, target: orgB });
        }
      }
    }
    
    setSuggestions(newSuggestions);
  }, [organizations]);

  const handleMergeClick = (source: Organization, target: Organization)
... (truncated — see full diff in files)
```

## Test Suggestions

Framework: `Jest with React Testing Library`

- **shouldDisplayWarningWhenEmailsDoNotMatch** *(edge case)* — Verifies that the safety check warning is displayed when there is an email mismatch between the merging organizations.
- **shouldCallOnConfirmWhenConfirmMergeIsClicked** — Ensures the confirm action works correctly and triggers the provided callback.
- **shouldCallOnCancelWhenCancelIsClicked** — Ensures the cancel action works correctly and triggers the provided callback to close the modal.
- **shouldOpenWarningModalWhenMergingMismatchedOrganizations** *(edge case)* — Integration test to ensure the merge tool correctly evaluates the email domains and passes the right state to the warning modal.

## Confluence Documentation References

- [Product Requirements Document for IDRE Dispute Platform's Organization Management System](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/302383114) — This PRD governs the Organization Management System, which is the core domain for the organization combine feature. It will need to be updated with the new merge logic and constraints.
- [IDRE Dispute Platform Release: Organization Management and Admin Tools Overview](https://orchidsoftware.atlassian.net/wiki/spaces/IDRE/pages/315654145) — This document provides an overview of the Organization Management and Admin Tools, which will house the new broader company-tab merge tool and warning modal.

**Suggested Documentation Updates:**

- Product Requirements Document for IDRE Dispute Platform's Organization Management System: Needs updating to include the new automated suggestion engine, the manual safety check workflow, and the rules for consolidating records, permissions, and billing history during an organization merge.
- IDRE Dispute Platform Release: Organization Management and Admin Tools Overview: Should be updated to reflect the new organization combine feature and the warning modal logic for administrators.

## AI Confidence Scores
Plan: 90%, Code: 95%, Tests: 95%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._