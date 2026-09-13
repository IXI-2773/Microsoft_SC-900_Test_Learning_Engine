# 02 — Current scope reconciliation

Authority compared:

- Live study guide: Skills measured as of July 28, 2026
- Repository taxonomy: `config/certifications/sc900-2026.json`

## Verified structure

Four weighted domains match the live guide:

- Security, compliance, and identity concepts (10–15%)
- Microsoft Entra (25–30%)
- Microsoft security solutions (35–40%)
- Microsoft compliance solutions (20–25%)

14 objectives and 58 unique leaves match. No taxonomy rewrite was performed.

`CURRENT_SC900_SCOPE_VERIFIED = YES`

## Recorded discrepancies (no silent rewrite)

1. **Security Copilot** appears on the current security-solutions learning path and is not a study-guide leaf. Inventoried as `exam_in_scope: false`. No Copilot questions approved.
2. **Purview Data Map / Unified Catalog** appears as a current compliance-path module. Study-guide leaves do not name those products. Inventoried out of exam-leaf scope.
3. **Global Secure Access / SSE** is taught in the Entra access module. Study-guide access leaves remain Conditional Access and Entra roles/RBAC only.
4. **Azure Key Vault** remains a study-guide leaf, but the current Azure infrastructure module units emphasize encryption rather than a named Key Vault unit. Product documentation is the answer authority.
5. Predecessor questions cite `explore-plan-compliance-microsoft-365`, which is still live but not listed on the current four-path cards.

Full record: `content/sc900/microsoft-learn-corpus/scope_reconciliation.json`
