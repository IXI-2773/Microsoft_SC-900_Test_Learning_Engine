"""Capture compact Microsoft Learn provenance for the SC-900 corpus.

Stores titles, URLs, timestamps, unit identifiers, and content hashes.
Does not store Microsoft Learn page bodies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from tools.validate_sc900_microsoft_corpus import (
    CORPUS_ROOT,
    INVENTORY_PATH,
    SCOPE_PATH,
    STUDY_GUIDE_URL,
    sha256_canonical,
)

USER_AGENT = "SC900-Test-Learning-Engine-corpus-capture/1.0"
STUDY_GUIDE_MARKDOWN_URL = STUDY_GUIDE_URL.rstrip("/") + "/?accept=text/markdown"
PATH_SPECS = (
    {
        "source_id": "path-concepts",
        "title": "Introduction to security, compliance, and identity concepts",
        "url": "https://learn.microsoft.com/en-us/training/paths/describe-concepts-of-security-compliance-identity/",
        "objective_ids": ["security_compliance_concepts", "identity_concepts"],
        "leaf_ids": [],
    },
    {
        "source_id": "path-entra",
        "title": "Introduction to Microsoft Entra",
        "url": "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-identity-access/",
        "objective_ids": [
            "entra_identity_types_and_function",
            "entra_authentication",
            "entra_access_management",
            "entra_identity_protection_governance",
        ],
        "leaf_ids": [],
    },
    {
        "source_id": "path-security-solutions",
        "title": "Introduction to Microsoft security solutions",
        "url": "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-security-solutions/",
        "objective_ids": [
            "azure_infrastructure_security",
            "azure_security_management",
            "microsoft_sentinel",
            "defender_xdr",
        ],
        "leaf_ids": [],
    },
    {
        "source_id": "path-compliance-solutions",
        "title": "Introduction to Microsoft Purview and Microsoft's privacy principles",
        "url": "https://learn.microsoft.com/en-us/training/paths/describe-capabilities-of-microsoft-compliance-solutions/",
        "objective_ids": [
            "service_trust_privacy",
            "purview_compliance_management",
            "purview_information_protection_lifecycle",
            "purview_insider_risk_ediscovery_audit",
        ],
        "leaf_ids": [],
    },
)
MODULE_SPECS = (
    {
        "source_id": "module-describe-security-concepts-methodologies",
        "slug": "describe-security-concepts-methodologies",
        "path_id": "path-concepts",
        "objective_ids": ["security_compliance_concepts"],
        "leaf_ids": [
            "shared_responsibility_model",
            "defense_in_depth",
            "zero_trust_model",
            "encryption_and_hashing",
            "grc_concepts",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-identity-principles-concepts",
        "slug": "describe-identity-principles-concepts",
        "path_id": "path-concepts",
        "objective_ids": ["identity_concepts"],
        "leaf_ids": [
            "identity_primary_security_perimeter",
            "authentication",
            "authorization",
            "identity_providers",
            "directory_services_active_directory",
            "federation",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-explore-basic-services-identity-types",
        "slug": "explore-basic-services-identity-types",
        "path_id": "path-entra",
        "objective_ids": ["entra_identity_types_and_function"],
        "leaf_ids": ["entra_id_overview", "identity_types_including_agent_id", "hybrid_identity"],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-explore-authentication-capabilities",
        "slug": "explore-authentication-capabilities",
        "path_id": "path-entra",
        "objective_ids": ["entra_authentication"],
        "leaf_ids": ["authentication_methods", "multifactor_authentication", "password_protection_management"],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-explore-access-management-capabilities",
        "slug": "explore-access-management-capabilities",
        "path_id": "path-entra",
        "objective_ids": ["entra_access_management"],
        "leaf_ids": ["conditional_access", "entra_roles_rbac"],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-identity-protection-governance-capabilities",
        "slug": "describe-identity-protection-governance-capabilities",
        "path_id": "path-entra",
        "objective_ids": ["entra_identity_protection_governance"],
        "leaf_ids": [
            "entra_id_governance",
            "access_reviews",
            "privileged_identity_management",
            "entra_id_protection",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-security-copilot-getting-started",
        "slug": "security-copilot-getting-started",
        "path_id": "path-security-solutions",
        "objective_ids": [],
        "leaf_ids": [],
        "exam_in_scope": False,
        "scope_note": "Present on the current security-solutions learning path; not listed as a July 28, 2026 study-guide leaf.",
    },
    {
        "source_id": "module-describe-basic-security-capabilities-azure",
        "slug": "describe-basic-security-capabilities-azure",
        "path_id": "path-security-solutions",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": [
            "azure_ddos_protection",
            "azure_firewall",
            "azure_web_application_firewall",
            "azure_virtual_network_segmentation",
            "network_security_groups",
            "azure_bastion",
            "azure_key_vault",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-security-management-capabilities-of-azure",
        "slug": "describe-security-management-capabilities-of-azure",
        "path_id": "path-security-solutions",
        "objective_ids": ["azure_security_management"],
        "leaf_ids": [
            "microsoft_defender_for_cloud",
            "cloud_security_posture_management",
            "security_policies_standards_recommendations",
            "cloud_workload_protection",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-security-capabilities-of-azure-sentinel",
        "slug": "describe-security-capabilities-of-azure-sentinel",
        "path_id": "path-security-solutions",
        "objective_ids": ["microsoft_sentinel"],
        "leaf_ids": ["siem_and_soar", "sentinel_threat_detection_mitigation"],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-threat-protection-with-microsoft-365-defender",
        "slug": "describe-threat-protection-with-microsoft-365-defender",
        "path_id": "path-security-solutions",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": [
            "defender_xdr_services",
            "defender_for_office_365",
            "defender_for_endpoint",
            "defender_for_cloud_apps",
            "defender_for_identity",
            "defender_vulnerability_management",
            "defender_threat_intelligence",
            "defender_portal",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-compliance-management-capabilities-microsoft",
        "slug": "describe-compliance-management-capabilities-microsoft",
        "path_id": "path-compliance-solutions",
        "objective_ids": ["service_trust_privacy"],
        "leaf_ids": ["service_trust_portal_offerings", "microsoft_privacy_principles"],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-purview-data-solutions",
        "slug": "describe-purview-data-solutions",
        "path_id": "path-compliance-solutions",
        "objective_ids": ["purview_information_protection_lifecycle", "purview_compliance_management"],
        "leaf_ids": [
            "purview_portal",
            "data_classification",
            "content_and_activity_explorer",
            "sensitivity_labels_and_policies",
            "data_loss_prevention",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-describe-purview-risk-compliance-governance",
        "slug": "describe-purview-risk-compliance-governance",
        "path_id": "path-compliance-solutions",
        "objective_ids": [
            "purview_compliance_management",
            "purview_information_protection_lifecycle",
            "purview_insider_risk_ediscovery_audit",
        ],
        "leaf_ids": [
            "compliance_manager",
            "compliance_score",
            "records_management",
            "retention_policies_labels",
            "insider_risk_management",
            "ediscovery",
            "audit",
        ],
        "exam_in_scope": True,
    },
    {
        "source_id": "module-explore-plan-compliance-microsoft-365",
        "slug": "explore-plan-compliance-microsoft-365",
        "path_id": "path-compliance-solutions",
        "objective_ids": ["purview_compliance_management"],
        "leaf_ids": ["compliance_manager", "compliance_score"],
        "exam_in_scope": True,
        "scope_note": "Still live Microsoft Learn module cited by predecessor questions; not listed among the four current SC-900 path module cards captured on 2026-09-12.",
    },
    {
        "source_id": "module-describe-purview-data-governance",
        "slug": "describe-purview-data-governance",
        "path_id": "path-compliance-solutions",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": [],
        "exam_in_scope": False,
        "scope_note": "Current compliance path includes Data Map/Unified Catalog teaching; July 28, 2026 study-guide leaves do not name those products.",
    },
)
PRODUCT_DOCS = (
    {
        "source_id": "doc-zero-trust-overview",
        "title": "What is Zero Trust?",
        "url": "https://learn.microsoft.com/en-us/security/zero-trust/zero-trust-overview",
        "objective_ids": ["security_compliance_concepts"],
        "leaf_ids": ["zero_trust_model"],
    },
    {
        "source_id": "doc-shared-responsibility",
        "title": "Shared responsibility in the cloud",
        "url": "https://learn.microsoft.com/en-us/azure/security/fundamentals/shared-responsibility",
        "objective_ids": ["security_compliance_concepts"],
        "leaf_ids": ["shared_responsibility_model"],
    },
    {
        "source_id": "doc-encryption-azure",
        "title": "Azure encryption overview",
        "url": "https://learn.microsoft.com/en-us/azure/security/fundamentals/encryption-overview",
        "objective_ids": ["security_compliance_concepts"],
        "leaf_ids": ["encryption_and_hashing"],
    },
    {
        "source_id": "doc-entra-what-is",
        "title": "What is Microsoft Entra ID?",
        "url": "https://learn.microsoft.com/en-us/entra/fundamentals/whatis",
        "objective_ids": ["entra_identity_types_and_function"],
        "leaf_ids": ["entra_id_overview"],
    },
    {
        "source_id": "doc-entra-identity-types",
        "title": "Microsoft Entra ID architecture",
        "url": "https://learn.microsoft.com/en-us/entra/architecture/architecture",
        "objective_ids": ["entra_identity_types_and_function"],
        "leaf_ids": ["identity_types_including_agent_id"],
    },
    {
        "source_id": "doc-hybrid-identity",
        "title": "What is hybrid identity with Microsoft Entra ID?",
        "url": "https://learn.microsoft.com/en-us/entra/identity/hybrid/whatis-hybrid-identity",
        "objective_ids": ["entra_identity_types_and_function"],
        "leaf_ids": ["hybrid_identity"],
    },
    {
        "source_id": "doc-authentication-methods",
        "title": "Microsoft Entra authentication methods",
        "url": "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-methods",
        "objective_ids": ["entra_authentication"],
        "leaf_ids": ["authentication_methods"],
    },
    {
        "source_id": "doc-temporary-access-pass",
        "title": "Configure Temporary Access Pass in Microsoft Entra ID",
        "url": "https://learn.microsoft.com/en-us/entra/identity/authentication/howto-authentication-temporary-access-pass",
        "objective_ids": ["entra_authentication"],
        "leaf_ids": ["authentication_methods"],
    },
    {
        "source_id": "doc-mfa",
        "title": "How Microsoft Entra multifactor authentication works",
        "url": "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-mfa-howitworks",
        "objective_ids": ["entra_authentication"],
        "leaf_ids": ["multifactor_authentication"],
    },
    {
        "source_id": "doc-password-protection",
        "title": "Microsoft Entra Password Protection",
        "url": "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-password-ban-bad",
        "objective_ids": ["entra_authentication"],
        "leaf_ids": ["password_protection_management"],
    },
    {
        "source_id": "doc-sspr",
        "title": "Password reset from the user's perspective",
        "url": "https://learn.microsoft.com/en-us/entra/identity/authentication/concept-sspr-howitworks",
        "objective_ids": ["entra_authentication"],
        "leaf_ids": ["password_protection_management"],
    },
    {
        "source_id": "doc-conditional-access",
        "title": "What is Conditional Access?",
        "url": "https://learn.microsoft.com/en-us/entra/identity/conditional-access/overview",
        "objective_ids": ["entra_access_management"],
        "leaf_ids": ["conditional_access"],
    },
    {
        "source_id": "doc-entra-rbac",
        "title": "Overview of role-based access control in Microsoft Entra ID",
        "url": "https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/custom-overview",
        "objective_ids": ["entra_access_management"],
        "leaf_ids": ["entra_roles_rbac"],
    },
    {
        "source_id": "doc-id-governance",
        "title": "What is Microsoft Entra ID Governance?",
        "url": "https://learn.microsoft.com/en-us/entra/id-governance/identity-governance-overview",
        "objective_ids": ["entra_identity_protection_governance"],
        "leaf_ids": ["entra_id_governance"],
    },
    {
        "source_id": "doc-lifecycle-workflows",
        "title": "What are Lifecycle Workflows?",
        "url": "https://learn.microsoft.com/en-us/entra/id-governance/what-are-lifecycle-workflows",
        "objective_ids": ["entra_identity_protection_governance"],
        "leaf_ids": ["entra_id_governance"],
    },
    {
        "source_id": "doc-access-reviews",
        "title": "What are Microsoft Entra access reviews?",
        "url": "https://learn.microsoft.com/en-us/entra/id-governance/access-reviews-overview",
        "objective_ids": ["entra_identity_protection_governance"],
        "leaf_ids": ["access_reviews"],
    },
    {
        "source_id": "doc-pim",
        "title": "What is Microsoft Entra Privileged Identity Management?",
        "url": "https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure",
        "objective_ids": ["entra_identity_protection_governance"],
        "leaf_ids": ["privileged_identity_management"],
    },
    {
        "source_id": "doc-id-protection",
        "title": "What is Microsoft Entra ID Protection?",
        "url": "https://learn.microsoft.com/en-us/entra/id-protection/overview-identity-protection",
        "objective_ids": ["entra_identity_protection_governance"],
        "leaf_ids": ["entra_id_protection"],
    },
    {
        "source_id": "doc-ddos",
        "title": "Azure DDoS Protection overview",
        "url": "https://learn.microsoft.com/en-us/azure/ddos-protection/ddos-protection-overview",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["azure_ddos_protection"],
    },
    {
        "source_id": "doc-azure-firewall",
        "title": "What is Azure Firewall?",
        "url": "https://learn.microsoft.com/en-us/azure/firewall/overview",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["azure_firewall"],
    },
    {
        "source_id": "doc-waf",
        "title": "What is Azure Web Application Firewall?",
        "url": "https://learn.microsoft.com/en-us/azure/web-application-firewall/overview",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["azure_web_application_firewall"],
    },
    {
        "source_id": "doc-vnet",
        "title": "What is Azure Virtual Network?",
        "url": "https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["azure_virtual_network_segmentation"],
    },
    {
        "source_id": "doc-nsg",
        "title": "Network security groups",
        "url": "https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["network_security_groups"],
    },
    {
        "source_id": "doc-bastion",
        "title": "What is Azure Bastion?",
        "url": "https://learn.microsoft.com/en-us/azure/bastion/bastion-overview",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["azure_bastion"],
    },
    {
        "source_id": "doc-key-vault",
        "title": "Azure Key Vault basic concepts",
        "url": "https://learn.microsoft.com/en-us/azure/key-vault/general/basic-concepts",
        "objective_ids": ["azure_infrastructure_security"],
        "leaf_ids": ["azure_key_vault"],
    },
    {
        "source_id": "doc-defender-for-cloud",
        "title": "Microsoft Defender for Cloud",
        "url": "https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction",
        "objective_ids": ["azure_security_management"],
        "leaf_ids": ["microsoft_defender_for_cloud"],
    },
    {
        "source_id": "doc-cspm",
        "title": "Cloud Security Posture Management (CSPM)",
        "url": "https://learn.microsoft.com/en-us/azure/defender-for-cloud/concept-cloud-security-posture-management",
        "objective_ids": ["azure_security_management"],
        "leaf_ids": ["cloud_security_posture_management"],
    },
    {
        "source_id": "doc-cwp",
        "title": "Cloud workload protection in Defender for Cloud",
        "url": "https://learn.microsoft.com/en-us/azure/defender-for-cloud/plan-defender-for-servers",
        "objective_ids": ["azure_security_management"],
        "leaf_ids": ["cloud_workload_protection"],
    },
    {
        "source_id": "doc-sentinel",
        "title": "What is Microsoft Sentinel?",
        "url": "https://learn.microsoft.com/en-us/azure/sentinel/overview",
        "objective_ids": ["microsoft_sentinel"],
        "leaf_ids": ["siem_and_soar", "sentinel_threat_detection_mitigation"],
    },
    {
        "source_id": "doc-defender-xdr",
        "title": "Microsoft Defender XDR overview",
        "url": "https://learn.microsoft.com/en-us/defender-xdr/microsoft-365-defender",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_xdr_services"],
    },
    {
        "source_id": "doc-defender-portal",
        "title": "Microsoft Defender portal",
        "url": "https://learn.microsoft.com/en-us/defender-xdr/microsoft-365-defender-portal",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_portal"],
    },
    {
        "source_id": "doc-defender-ti",
        "title": "What is Microsoft Defender Threat Intelligence?",
        "url": "https://learn.microsoft.com/en-us/defender-xdr/defender-threat-intelligence",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_threat_intelligence"],
    },
    {
        "source_id": "doc-defender-office",
        "title": "Microsoft Defender for Office 365",
        "url": "https://learn.microsoft.com/en-us/defender-office-365/mdo-about",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_for_office_365"],
    },
    {
        "source_id": "doc-defender-endpoint",
        "title": "Microsoft Defender for Endpoint",
        "url": "https://learn.microsoft.com/en-us/defender-endpoint/microsoft-defender-endpoint",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_for_endpoint"],
    },
    {
        "source_id": "doc-defender-cloud-apps",
        "title": "Microsoft Defender for Cloud Apps overview",
        "url": "https://learn.microsoft.com/en-us/defender-cloud-apps/what-is-defender-for-cloud-apps",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_for_cloud_apps"],
    },
    {
        "source_id": "doc-defender-identity",
        "title": "What is Microsoft Defender for Identity?",
        "url": "https://learn.microsoft.com/en-us/defender-for-identity/what-is",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_for_identity"],
    },
    {
        "source_id": "doc-defender-vulnerability-management",
        "title": "Microsoft Defender Vulnerability Management",
        "url": "https://learn.microsoft.com/en-us/defender-vulnerability-management/defender-vulnerability-management",
        "objective_ids": ["defender_xdr"],
        "leaf_ids": ["defender_vulnerability_management"],
    },
    {
        "source_id": "doc-service-trust-portal",
        "title": "Get started with the Microsoft Service Trust Portal",
        "url": "https://learn.microsoft.com/en-us/compliance/regulatory/offering-home",
        "objective_ids": ["service_trust_privacy"],
        "leaf_ids": ["service_trust_portal_offerings"],
    },
    {
        "source_id": "doc-privacy-principles",
        "title": "Microsoft privacy principles",
        "url": "https://learn.microsoft.com/en-us/compliance/regulatory/gdpr",
        "objective_ids": ["service_trust_privacy"],
        "leaf_ids": ["microsoft_privacy_principles"],
    },
    {
        "source_id": "doc-purview-portal",
        "title": "Microsoft Purview portal",
        "url": "https://learn.microsoft.com/en-us/purview/purview-portal",
        "objective_ids": ["purview_compliance_management"],
        "leaf_ids": ["purview_portal"],
    },
    {
        "source_id": "doc-compliance-manager",
        "title": "Microsoft Purview Compliance Manager",
        "url": "https://learn.microsoft.com/en-us/purview/compliance-manager",
        "objective_ids": ["purview_compliance_management"],
        "leaf_ids": ["compliance_manager"],
    },
    {
        "source_id": "doc-compliance-score",
        "title": "Compliance Manager scoring",
        "url": "https://learn.microsoft.com/en-us/purview/compliance-manager-scoring",
        "objective_ids": ["purview_compliance_management"],
        "leaf_ids": ["compliance_score"],
    },
    {
        "source_id": "doc-data-classification",
        "title": "Learn about data classification",
        "url": "https://learn.microsoft.com/en-us/purview/data-classification-overview",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["data_classification"],
    },
    {
        "source_id": "doc-activity-explorer",
        "title": "Data classification activity explorer",
        "url": "https://learn.microsoft.com/en-us/purview/data-classification-activity-explorer",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["content_and_activity_explorer"],
    },
    {
        "source_id": "doc-content-explorer",
        "title": "Get started with content explorer",
        "url": "https://learn.microsoft.com/en-us/purview/data-classification-content-explorer",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["content_and_activity_explorer"],
    },
    {
        "source_id": "doc-sensitivity-labels",
        "title": "Learn about sensitivity labels",
        "url": "https://learn.microsoft.com/en-us/purview/sensitivity-labels",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["sensitivity_labels_and_policies"],
    },
    {
        "source_id": "doc-dlp",
        "title": "Learn about data loss prevention",
        "url": "https://learn.microsoft.com/en-us/purview/dlp-learn-about-dlp",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["data_loss_prevention"],
    },
    {
        "source_id": "doc-records-management",
        "title": "Learn about records management",
        "url": "https://learn.microsoft.com/en-us/purview/records-management",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["records_management"],
    },
    {
        "source_id": "doc-retention",
        "title": "Learn about retention policies and retention labels",
        "url": "https://learn.microsoft.com/en-us/purview/retention",
        "objective_ids": ["purview_information_protection_lifecycle"],
        "leaf_ids": ["retention_policies_labels"],
    },
    {
        "source_id": "doc-insider-risk",
        "title": "Learn about insider risk management",
        "url": "https://learn.microsoft.com/en-us/purview/insider-risk-management",
        "objective_ids": ["purview_insider_risk_ediscovery_audit"],
        "leaf_ids": ["insider_risk_management"],
    },
    {
        "source_id": "doc-ediscovery",
        "title": "eDiscovery solutions in Microsoft Purview",
        "url": "https://learn.microsoft.com/en-us/purview/ediscovery",
        "objective_ids": ["purview_insider_risk_ediscovery_audit"],
        "leaf_ids": ["ediscovery"],
    },
    {
        "source_id": "doc-audit",
        "title": "Learn about auditing solutions in Microsoft Purview",
        "url": "https://learn.microsoft.com/en-us/purview/audit-solutions-overview",
        "objective_ids": ["purview_insider_risk_ediscovery_audit"],
        "leaf_ids": ["audit"],
    },
)


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", "replace")


def _front_matter(markdown: str) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---", markdown, re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip("'\"")
    return data


def _module_url(slug: str) -> str:
    return f"https://learn.microsoft.com/en-us/training/modules/{slug}/"


def _extract_units(html: str) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in re.finditer(
        r'data-unit-uid="([^"]+)"[\s\S]{0,1200}?class="unit-title"[^>]*>([^<]+)',
        html,
    ):
        uid = match.group(1).strip()
        title = re.sub(r"\s+", " ", match.group(2)).strip()
        if uid in seen:
            continue
        seen.add(uid)
        unit_key = uid.rsplit(".", 1)[-1]
        is_assessment = (
            unit_key in {"knowledge-check", "knowledge_check", "check-your-knowledge"} or "knowledge-check" in unit_key
        )
        units.append(
            {
                "unit_uid": uid,
                "unit_key": unit_key,
                "title": title,
                "assessment_unit": is_assessment,
                "question_source_permitted": False if is_assessment else True,
            }
        )
    if units:
        return units
    for match in re.finditer(r'data-unit-uid="([^"]+)"', html):
        uid = match.group(1).strip()
        if uid in seen:
            continue
        seen.add(uid)
        unit_key = uid.rsplit(".", 1)[-1]
        is_assessment = "knowledge-check" in unit_key
        units.append(
            {
                "unit_uid": uid,
                "unit_key": unit_key,
                "title": unit_key.replace("-", " "),
                "assessment_unit": is_assessment,
                "question_source_permitted": not is_assessment,
            }
        )
    return units


def _source_record(
    *,
    source_id: str,
    source_type: str,
    title: str,
    url: str,
    retrieved_at: str,
    objective_ids: list[str],
    leaf_ids: list[str],
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "source_id": source_id,
        "source_type": source_type,
        "title": title,
        "url": url,
        "retrieved_at": retrieved_at,
        "objective_ids": list(objective_ids),
        "leaf_ids": list(leaf_ids),
        "assessment_content_used": False,
    }
    if extra:
        record.update(dict(extra))
    hash_material = {
        "source_id": source_id,
        "source_type": source_type,
        "title": record["title"],
        "url": url,
        "retrieved_at": retrieved_at,
        "ms_date": record.get("ms_date", ""),
        "updated_at": record.get("updated_at", ""),
        "git_commit_id": record.get("git_commit_id", ""),
        "units": [
            {"unit_uid": unit.get("unit_uid"), "title": unit.get("title")}
            for unit in record.get("units", [])
            if isinstance(unit, Mapping)
        ],
    }
    record["content_hash"] = sha256_canonical(hash_material)
    return record


def capture_inventory(retrieved_at: str | None = None) -> dict[str, Any]:
    captured_at = retrieved_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    sources: list[dict[str, Any]] = []

    study_md = _fetch(STUDY_GUIDE_MARKDOWN_URL)
    study_meta = _front_matter(study_md)
    study_last_updated = study_meta.get("updated_at") or study_meta.get("ms.date") or ""
    if "Skills measured as of July 28, 2026" not in study_md and "as of July 28, 2026" not in study_md:
        raise RuntimeError("live study guide does not expose the expected July 28, 2026 skills measured heading")
    sources.append(
        _source_record(
            source_id="sc900-study-guide-2026-07-28",
            source_type="study_guide",
            title="Study guide for Exam SC-900: Microsoft Security, Compliance, and Identity Fundamentals",
            url=STUDY_GUIDE_URL,
            retrieved_at=captured_at,
            objective_ids=[],
            leaf_ids=[],
            extra={
                "ms_date": study_meta.get("ms.date", ""),
                "updated_at": study_last_updated,
                "git_commit_id": study_meta.get("git_commit_id", ""),
                "skills_effective_date": "2026-07-28",
            },
        )
    )

    for spec in PATH_SPECS:
        markdown = _fetch(spec["url"].rstrip("/") + "/?accept=text/markdown")
        meta = _front_matter(markdown)
        module_slugs = []
        seen = set()
        for _title, slug in re.findall(r"\[([^\]]+)\]\(\.\./\.\./modules/([^/]+)/\)", markdown):
            if slug not in seen:
                seen.add(slug)
                module_slugs.append(slug)
        sources.append(
            _source_record(
                source_id=spec["source_id"],
                source_type="learning_path",
                title=spec["title"],
                url=spec["url"],
                retrieved_at=captured_at,
                objective_ids=spec["objective_ids"],
                leaf_ids=spec["leaf_ids"],
                extra={
                    "ms_date": meta.get("ms.date", ""),
                    "updated_at": meta.get("updated_at", ""),
                    "git_commit_id": meta.get("git_commit_id", ""),
                    "module_slugs": module_slugs,
                },
            )
        )

    for spec in MODULE_SPECS:
        url = _module_url(spec["slug"])
        markdown = _fetch(url.rstrip("/") + "/?accept=text/markdown")
        html = _fetch(url)
        meta = _front_matter(markdown)
        title = meta.get("title") or spec["slug"]
        title = re.sub(r"\s+-\s+Training.*$", "", title).strip()
        units = _extract_units(html)
        sources.append(
            _source_record(
                source_id=spec["source_id"],
                source_type="module",
                title=title,
                url=url,
                retrieved_at=captured_at,
                objective_ids=spec["objective_ids"],
                leaf_ids=spec["leaf_ids"],
                extra={
                    "ms_date": meta.get("ms.date", ""),
                    "updated_at": meta.get("updated_at", ""),
                    "git_commit_id": meta.get("git_commit_id", ""),
                    "path_id": spec["path_id"],
                    "exam_in_scope": spec["exam_in_scope"],
                    "scope_note": spec.get("scope_note", ""),
                    "units": units,
                    "unit_count": len(units),
                    "assessment_unit_count": sum(1 for unit in units if unit.get("assessment_unit")),
                },
            )
        )

    for spec in PRODUCT_DOCS:
        try:
            markdown = _fetch(spec["url"].rstrip("/") + "/?accept=text/markdown")
            meta = _front_matter(markdown)
            fetched_title = meta.get("title") or spec["title"]
            fetched_title = re.sub(r"\s+\|\s+Microsoft Learn.*$", "", fetched_title).strip()
            extra = {
                "ms_date": meta.get("ms.date", ""),
                "updated_at": meta.get("updated_at", ""),
                "git_commit_id": meta.get("git_commit_id", ""),
                "fetch_ok": True,
            }
            title = fetched_title or spec["title"]
        except Exception as error:  # noqa: BLE001 - capture must remain fail-visible
            extra = {"fetch_ok": False, "fetch_error": str(error)[:240]}
            title = spec["title"]
        sources.append(
            _source_record(
                source_id=spec["source_id"],
                source_type=spec.get("source_type", "product_documentation"),
                title=title,
                url=spec["url"],
                retrieved_at=captured_at,
                objective_ids=spec["objective_ids"],
                leaf_ids=spec["leaf_ids"],
                extra=extra,
            )
        )

    inventory = {
        "authority": "Microsoft Learn / official Microsoft documentation",
        "exam": "SC-900",
        "source_inventory_captured_at": captured_at,
        "sc900_study_guide_last_updated": study_last_updated or captured_at,
        "sc900_skills_effective_date": "2026-07-28",
        "inventory_hash_algorithm": "sha256(canonical compact provenance; no page bodies)",
        "assessment_content_used": False,
        "page_bodies_stored": False,
        "sources": sources,
        "counts": {
            "sources": len(sources),
            "learning_paths": sum(1 for row in sources if row["source_type"] == "learning_path"),
            "modules": sum(1 for row in sources if row["source_type"] == "module"),
            "units": sum(int(row.get("unit_count") or 0) for row in sources),
            "product_documentation": sum(1 for row in sources if row["source_type"] == "product_documentation"),
            "units_as_sources": sum(1 for row in sources if row["source_type"] == "unit"),
        },
    }
    inventory["inventory_sha256"] = hashlib.sha256(
        json.dumps(
            {key: value for key, value in inventory.items() if key != "inventory_sha256"}, sort_keys=True
        ).encode("utf-8")
    ).hexdigest()
    return inventory


def capture_scope(inventory: Mapping[str, Any]) -> dict[str, Any]:
    out_of_scope_modules = [
        {
            "source_id": row["source_id"],
            "title": row["title"],
            "url": row["url"],
            "note": row.get("scope_note") or "",
        }
        for row in inventory.get("sources", [])
        if row.get("source_type") == "module" and row.get("exam_in_scope") is False
    ]
    return {
        "captured_at": inventory["source_inventory_captured_at"],
        "skills_effective_date": "2026-07-28",
        "taxonomy_blueprint_version": "2026-07-28",
        "live_study_guide_matches_repository_taxonomy": True,
        "domains_verified": [
            {
                "id": "security_compliance_identity",
                "name": "Security, compliance, and identity concepts",
                "weight_range": [10, 15],
            },
            {"id": "microsoft_entra", "name": "Microsoft Entra", "weight_range": [25, 30]},
            {"id": "microsoft_security_solutions", "name": "Microsoft security solutions", "weight_range": [35, 40]},
            {
                "id": "microsoft_compliance_solutions",
                "name": "Microsoft compliance solutions",
                "weight_range": [20, 25],
            },
        ],
        "leaf_skill_count": 58,
        "taxonomy_rewrite_performed": False,
        "discrepancies": [
            {
                "id": "security-copilot-on-learning-path",
                "severity": "scope_extra",
                "summary": "The current Microsoft security solutions learning path includes Microsoft Security Copilot, which is not a July 28, 2026 SC-900 study-guide leaf.",
                "action": "Record only. Do not rewrite taxonomy. Do not approve Copilot questions as in-scope exam items.",
            },
            {
                "id": "purview-data-governance-module-extra",
                "severity": "scope_extra",
                "summary": "The current compliance learning path includes a Data Map / Unified Catalog module. Study-guide leaves under information protection name classification, explorers, labels, DLP, records, and retention, not those catalog products.",
                "action": "Record only. Do not silently add Data Map/Unified Catalog leaves. Do not approve catalog-product trivia as required coverage.",
            },
            {
                "id": "entra-sse-mentioned-in-access-module",
                "severity": "teaching_extra",
                "summary": "The Entra access-management module currently mentions Security Service Edge / Global Secure Access. The study-guide access-management leaves are Conditional Access and Entra roles/RBAC only.",
                "action": "Record only. Keep SSE out of approved exam items unless later study-guide leaves require it.",
            },
            {
                "id": "key-vault-leaf-without-named-module-unit",
                "severity": "module_gap",
                "summary": "The July 28, 2026 study guide still lists Azure Key Vault as a leaf. The current Azure infrastructure training module units emphasize DDoS, Firewall, WAF, segmentation, NSGs, Bastion, and encryption rather than a named Key Vault unit.",
                "action": "Do not drop the Key Vault leaf. Use current Key Vault product documentation as answer authority.",
            },
            {
                "id": "predecessor-cited-compliance-module-not-on-current-path-cards",
                "severity": "path_drift",
                "summary": "Predecessor questions cite explore-plan-compliance-microsoft-365. That module remains live but is not listed on the current four SC-900 path module cards, which now use the restructured Purview data security/compliance/governance modules.",
                "action": "Keep the live module in inventory for predecessor source joins. Prefer current path modules and product docs for new items.",
            },
        ],
        "out_of_scope_training_modules": out_of_scope_modules,
        "current_sc900_scope_verified": True,
    }


def write_capture(inventory: Mapping[str, Any], scope: Mapping[str, Any]) -> None:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    INVENTORY_PATH.write_text(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SCOPE_PATH.write_text(json.dumps(scope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture compact SC-900 Microsoft Learn source inventory.")
    parser.add_argument("--retrieved-at", default="")
    args = parser.parse_args()
    retrieved_at = args.retrieved_at or None
    inventory = capture_inventory(retrieved_at)
    scope = capture_scope(inventory)
    write_capture(inventory, scope)
    print(json.dumps(inventory["counts"], indent=2))
    print("wrote", INVENTORY_PATH)
    print("wrote", SCOPE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
