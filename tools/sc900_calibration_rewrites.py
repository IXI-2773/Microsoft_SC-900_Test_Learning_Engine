from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from tools.sc900_exam_calibration import (
    APPLIED,
    CALIBRATION_ROOT,
    CALIBRATION_VERSION,
    COMPILED_BANK_PATH,
    CORE,
    PRECALIBRATION_BANK_SHA256,
    STRETCH,
    classify_distractor,
    exam_simulation_eligible,
    load_json,
    load_store_difficulty,
    sha256_file,
    write_json,
)

STRETCH_KEEP = {
    "sc900_mlc_q102",
    "sc900_mlc_q143",
    "sc900_mlc_q148",
    "sc900_mlc_q171",
    "sc900_mlc_q173",
    "sc900_mlc_q202",
    "sc900_mlc_q214",
    "sc900_mlc_q246",
    "sc900_mlc_q253",
    "sc900_mlc_q261",
    "sc900_mlc_q262",
    "sc900_mlc_q264",
    "sc900_mlc_q272",
    "sc900_mlc_q274",
    "sc900_mlc_q275",
    "sc900_mlc_q276",
    "sc900_mlc_q279",
    "sc900_mlc_q285",
    "sc900_mlc_q286",
    "sc900_mlc_q289",
    "sc900_mlc_q290",
    "sc900_mlc_q298",
    "sc900_p3_q084",
}

DIRECT_STYLES = {
    "direct_concept",
    "capability_selection",
    "service_selection",
    "current_topic",
    "misconception_correction",
}

LEAF_NEIGHBORS: dict[str, tuple[str, ...]] = {
    "access_reviews": (
        "Privileged Identity Management eligible-role activation",
        "Entitlement management access packages",
        "Microsoft Entra ID Protection risk detection",
        "Lifecycle workflows for joiner and leaver tasks",
    ),
    "audit": (
        "Data loss prevention",
        "eDiscovery content collection",
        "Insider Risk Management",
        "Retention policies",
    ),
    "authentication": (
        "Authorization",
        "Federation",
        "Conditional Access",
        "Data classification",
    ),
    "authentication_methods": (
        "Temporary Access Pass",
        "Windows Hello for Business",
        "Microsoft Authenticator passwordless sign-in",
        "Self-service password reset",
    ),
    "authorization": (
        "Authentication",
        "Federation",
        "Conditional Access",
        "Privileged Identity Management",
    ),
    "azure_bastion": (
        "Network security groups",
        "Azure Firewall",
        "Azure DDoS Protection",
        "Azure Web Application Firewall",
    ),
    "azure_ddos_protection": (
        "Azure Web Application Firewall",
        "Azure Firewall",
        "Network security groups",
        "Azure Bastion",
    ),
    "azure_firewall": (
        "Network security groups",
        "Azure Web Application Firewall",
        "Azure DDoS Protection",
        "Azure Bastion",
    ),
    "azure_key_vault": (
        "Microsoft Entra ID",
        "Azure Disk Encryption",
        "Certificates stored in application source code",
        "Microsoft Defender for Cloud",
    ),
    "azure_virtual_network_segmentation": (
        "Network security groups",
        "Azure Firewall",
        "Azure Bastion",
        "Azure DDoS Protection",
    ),
    "azure_web_application_firewall": (
        "Azure Firewall",
        "Azure DDoS Protection",
        "Network security groups",
        "Azure Bastion",
    ),
    "cloud_security_posture_management": (
        "Cloud workload protection",
        "Microsoft Defender for Endpoint",
        "Microsoft Sentinel",
        "Compliance Manager",
    ),
    "cloud_workload_protection": (
        "Cloud security posture management",
        "Microsoft Defender for Endpoint",
        "Microsoft Sentinel",
        "Azure Policy",
    ),
    "compliance_manager": (
        "Service Trust Portal",
        "Compliance score",
        "Microsoft Purview Audit",
        "Microsoft Defender for Cloud recommendations",
    ),
    "compliance_score": (
        "Compliance Manager improvement actions",
        "Service Trust Portal audit reports",
        "Defender for Cloud secure score",
        "Purview data classification",
    ),
    "conditional_access": (
        "Privileged Identity Management",
        "Microsoft Entra ID Protection",
        "Access reviews",
        "Self-service password reset",
    ),
    "content_and_activity_explorer": (
        "Data loss prevention policies",
        "Sensitivity labels",
        "Retention policies",
        "Microsoft Purview Audit",
    ),
    "data_classification": (
        "Sensitivity labels",
        "Data loss prevention",
        "Retention labels",
        "Records management",
    ),
    "data_loss_prevention": (
        "Sensitivity labels",
        "Retention policies",
        "Insider Risk Management",
        "Microsoft Purview Audit",
    ),
    "defender_for_cloud_apps": (
        "Microsoft Defender for Office 365",
        "Microsoft Defender for Endpoint",
        "Microsoft Defender for Identity",
        "Microsoft Defender for Cloud",
    ),
    "defender_for_endpoint": (
        "Microsoft Defender for Identity",
        "Microsoft Defender for Office 365",
        "Microsoft Defender Vulnerability Management",
        "Microsoft Defender for Cloud Apps",
    ),
    "defender_for_identity": (
        "Microsoft Defender for Endpoint",
        "Microsoft Entra ID Protection",
        "Microsoft Defender for Cloud Apps",
        "Microsoft Entra Connect",
    ),
    "defender_for_office_365": (
        "Microsoft Defender for Endpoint",
        "Microsoft Defender for Cloud Apps",
        "Microsoft Defender for Identity",
        "Azure Web Application Firewall",
    ),
    "defender_portal": (
        "Microsoft Defender XDR",
        "Microsoft Sentinel",
        "Service Trust Portal",
        "Microsoft Purview portal",
    ),
    "defender_threat_intelligence": (
        "Microsoft Defender for Office 365 Safe Links",
        "Microsoft Sentinel analytics rules",
        "Microsoft Defender for Endpoint",
        "Microsoft Defender XDR incidents",
    ),
    "defender_vulnerability_management": (
        "Microsoft Defender for Endpoint",
        "Microsoft Defender for Office 365",
        "Microsoft Defender for Cloud",
        "Microsoft Defender for Identity",
    ),
    "defender_xdr_services": (
        "Microsoft Defender for Endpoint",
        "Microsoft Defender for Office 365",
        "Microsoft Defender for Identity",
        "Microsoft Defender for Cloud Apps",
    ),
    "defense_in_depth": (
        "Zero Trust",
        "Shared responsibility model",
        "Least privilege",
        "Encryption",
    ),
    "directory_services_active_directory": (
        "Microsoft Entra ID",
        "Microsoft Entra Domain Services",
        "Microsoft Entra Connect",
        "Microsoft Defender for Identity",
    ),
    "ediscovery": (
        "Microsoft Purview Audit",
        "Insider Risk Management",
        "Data loss prevention",
        "Retention policies",
    ),
    "encryption_and_hashing": (
        "Hashing for integrity",
        "Encryption for confidentiality",
        "Azure Key Vault",
        "Sensitivity labels",
    ),
    "entra_id_governance": (
        "Access reviews",
        "Entitlement management",
        "Privileged Identity Management",
        "Lifecycle workflows",
    ),
    "entra_id_overview": (
        "Active Directory Domain Services",
        "Microsoft Entra Domain Services",
        "Microsoft Entra External ID",
        "Microsoft Intune",
    ),
    "entra_id_protection": (
        "Conditional Access",
        "Privileged Identity Management",
        "Microsoft Defender for Identity",
        "Access reviews",
    ),
    "entra_roles_rbac": (
        "Azure role-based access control",
        "Privileged Identity Management",
        "Access reviews",
        "Conditional Access",
    ),
    "federation": (
        "Authentication",
        "Authorization",
        "Microsoft Entra ID",
        "Hybrid identity",
    ),
    "grc_concepts": (
        "Policies",
        "Standards",
        "Regulations",
        "Compliance Manager",
    ),
    "hybrid_identity": (
        "Microsoft Entra Connect",
        "Password hash synchronization",
        "Pass-through authentication",
        "Federation with AD FS",
    ),
    "identity_primary_security_perimeter": (
        "Zero Trust",
        "Network firewall perimeter",
        "Conditional Access",
        "Defense in depth",
    ),
    "identity_providers": (
        "Microsoft Entra ID",
        "Federation",
        "Active Directory Domain Services",
        "Microsoft accounts",
    ),
    "identity_types_including_agent_id": (
        "User identities",
        "Workload identities",
        "Managed identities",
        "Agent identities",
    ),
    "insider_risk_management": (
        "Data loss prevention",
        "eDiscovery",
        "Microsoft Purview Audit",
        "Communication compliance",
    ),
    "microsoft_defender_for_cloud": (
        "Microsoft Defender XDR",
        "Microsoft Sentinel",
        "Microsoft Defender for Endpoint",
        "Compliance Manager",
    ),
    "microsoft_privacy_principles": (
        "Compliance Manager",
        "Service Trust Portal",
        "Data loss prevention",
        "Microsoft Purview Audit",
    ),
    "multifactor_authentication": (
        "Self-service password reset",
        "Password protection",
        "Conditional Access",
        "Windows Hello for Business",
    ),
    "network_security_groups": (
        "Azure Firewall",
        "Azure Web Application Firewall",
        "Azure DDoS Protection",
        "Azure Bastion",
    ),
    "password_protection_management": (
        "Self-service password reset",
        "Multifactor authentication",
        "Custom banned password list",
        "Conditional Access",
    ),
    "privileged_identity_management": (
        "Access reviews",
        "Entitlement management",
        "Microsoft Entra ID Protection",
        "Azure role-based access control",
    ),
    "purview_portal": (
        "Microsoft Entra admin center",
        "Microsoft Defender portal",
        "Service Trust Portal",
        "Azure portal virtual machine settings",
    ),
    "records_management": (
        "Retention labels",
        "Retention policies",
        "Data loss prevention",
        "eDiscovery holds",
    ),
    "retention_policies_labels": (
        "Data loss prevention",
        "Records management",
        "Sensitivity labels",
        "Microsoft Purview Audit",
    ),
    "security_policies_standards_recommendations": (
        "Regulations",
        "Industry standards",
        "Organizational security policies",
        "Compliance Manager",
    ),
    "sensitivity_labels_and_policies": (
        "Data loss prevention",
        "Retention labels",
        "Data classification",
        "Records management",
    ),
    "sentinel_threat_detection_mitigation": (
        "Microsoft Defender XDR",
        "Microsoft Defender for Cloud",
        "SIEM analytics rules",
        "SOAR playbooks",
    ),
    "service_trust_portal_offerings": (
        "Compliance Manager",
        "Microsoft Purview portal",
        "Microsoft Defender portal",
        "Microsoft Entra admin center",
    ),
    "shared_responsibility_model": (
        "Customer responsibility for data and identities",
        "Provider responsibility for physical datacenters",
        "SaaS versus IaaS responsibility split",
        "Zero Trust",
    ),
    "siem_and_soar": (
        "Microsoft Sentinel",
        "Microsoft Defender XDR",
        "Microsoft Defender for Cloud",
        "Azure Monitor",
    ),
    "zero_trust_model": (
        "Verify explicitly",
        "Use least-privilege access",
        "Assume breach",
        "Trusted corporate network perimeter",
    ),
}

STEM_REWRITES: dict[str, dict[str, Any]] = {
    "sc900_mlc_q201": {
        "stem": "An organization wants users to receive only the permissions required for their work. Which Zero Trust principle addresses this requirement?",
        "choices": {
            "A": "Use least-privilege access",
            "B": "Verify explicitly",
            "C": "Assume breach",
            "D": "Trust the corporate network by default",
        },
        "stem_style": "direct_concept",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 0,
        "reason": "Reduce two-step missing-principle diagnosis to one least-privilege recognition item.",
    },
    "sc900_mlc_q043": {
        "stem": "Identity Protection flags impossible-travel sign-ins as high risk. Which Entra capability can require extra controls or block those sign-ins?",
        "choices": {
            "A": "Conditional Access",
            "B": "Privileged Identity Management",
            "C": "Access reviews",
            "D": "Entitlement management",
        },
        "stem_style": "capability_selection",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask the Conditional Access response to ID Protection risk instead of a two-product pairing with joke distractors.",
    },
    "sc900_mlc_q068": {
        "choices": {
            "A": "Lifecycle Workflows recertify standing access; access reviews automate joiner and leaver tasks",
            "B": "Lifecycle Workflows automate joiner/mover/leaver tasks; access reviews recertify whether access is still needed",
            "C": "Lifecycle Workflows replace Privileged Identity Management; access reviews replace Conditional Access",
            "D": "Both capabilities are Microsoft Entra ID Protection risk policies",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the governance pairing decision; replace cross-product joke options with neighboring wrong pairings.",
    },
    "sc900_mlc_q111": {
        "choices": {
            "A": "SIEM automates containment; SOAR only stores logs",
            "B": "SIEM detects and investigates; SOAR automates response",
            "C": "SIEM is Microsoft Defender for Cloud Apps; SOAR is Azure Web Application Firewall",
            "D": "SIEM replaces Microsoft Entra ID as the identity provider",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the SIEM/SOAR pairing; replace unrelated-product distractors.",
    },
    "sc900_mlc_q157": {
        "choices": {
            "A": "Content explorer shows where classified items are; Activity explorer shows what is happening to labeled or classified content",
            "B": "Content explorer creates DLP policies; Activity explorer creates retention labels",
            "C": "Content explorer issues Entra roles; Activity explorer activates PIM",
            "D": "Both explorers replace sensitivity labels",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the explorer pairing; replace network-security joke distractors.",
    },
    "sc900_mlc_q165": {
        "choices": {
            "A": "Service Trust Portal configures tenant DLP; Compliance Manager publishes Microsoft's ISO reports",
            "B": "Compliance Manager is a DDoS mitigation service; Service Trust Portal is Defender XDR",
            "C": "Both replace Microsoft Entra ID",
            "D": "Service Trust Portal publishes Microsoft's audit evidence; Compliance Manager tracks the customer's implemented controls",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the STP versus Compliance Manager pairing; replace unrelated-product distractors.",
    },
    "sc900_mlc_q172": {
        "choices": {
            "A": "Insider Risk Management holds mailboxes for lawsuits; eDiscovery scores internal behavior",
            "B": "Insider Risk Management is Azure DDoS Protection; eDiscovery is Azure Firewall",
            "C": "eDiscovery issues Temporary Access Pass codes; Insider Risk Management issues FIDO2 keys",
            "D": "Insider Risk Management looks for internal risky behavior; eDiscovery collects content for legal matters",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the IRM versus eDiscovery pairing; replace joke distractors with swapped or neighboring wrong options.",
    },
    "sc900_mlc_q205": {
        "stem": "A contractor signs in successfully with MFA but cannot open a payroll app. Which process determines what the contractor may access?",
        "choices": {
            "A": "Authentication, which already granted every app permission",
            "B": "Authorization, which still evaluates roles and policies after sign-in",
            "C": "Federation, which always grants Global Administrator rights after sign-in",
            "D": "Conditional Access named locations, which replace role assignments",
        },
        "stem_style": "distinction_comparison",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Remove claim-diagnosis; test authorization directly after a successful sign-in.",
    },
    "sc900_mlc_q209": {
        "stem": "Which statement correctly distinguishes Active Directory Domain Services from Microsoft Entra ID?",
        "choices": {
            "A": "AD DS is only a Conditional Access grant control, and Entra ID is only a firewall",
            "B": "Entra ID exists only to host Azure Firewall policies",
            "C": "AD DS is the traditional on-premises directory service; Entra ID is Microsoft's cloud identity service and they are not the same thing",
            "D": "AD DS and Entra ID are both names for Microsoft Defender for Identity",
        },
        "stem_style": "concept_distinction",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask the AD DS versus Entra distinction without a learner-claim wrapper.",
    },
    "sc900_mlc_q222": {
        "choices": {
            "A": "Self-service password reset is the banned-password dictionary, and password protection is eDiscovery hold",
            "B": "Self-service password reset addresses forgotten-password recovery; password protection bans weak or custom banned terms",
            "C": "Self-service password reset recertifies guest groups; password protection activates privileged roles",
            "D": "Password protection issues Temporary Access Pass codes; self-service password reset is Conditional Access",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the SSPR versus password-protection pairing; replace cross-product joke distractors.",
    },
    "sc900_mlc_q230": {
        "stem": "Identity Protection marks a user high risk because leaked credentials were found. Which Entra capability can block that sign-in or require a secure password reset?",
        "choices": {
            "A": "Privileged Identity Management",
            "B": "Conditional Access",
            "C": "Access reviews",
            "D": "Entitlement management",
        },
        "stem_style": "capability_selection",
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Ask the Conditional Access response to user risk without a two-product pairing stem.",
    },
    "sc900_mlc_q234": {
        "stem": "Which Microsoft capability evaluates sign-in conditions such as user, device, location, and risk before granting access?",
        "choices": {
            "A": "Conditional Access",
            "B": "Sensitivity labels",
            "C": "Data loss prevention",
            "D": "Records management",
        },
        "stem_style": "capability_selection",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 0,
        "reason": "Ask for Conditional Access directly instead of correcting a classification/DLP claim.",
    },
    "sc900_mlc_q238": {
        "stem": "A user completes MFA and is then denied access to a finance SharePoint site. Which process denied the access?",
        "choices": {
            "A": "Authentication",
            "B": "Data loss prevention",
            "C": "Federation",
            "D": "Authorization",
        },
        "stem_style": "distinction_comparison",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Test authorization after MFA without diagnosing a helpdesk claim.",
    },
    "sc900_mlc_q244": {
        "stem": "Developers want a custom app to sign users in without storing passwords in the app. Which approach should they use?",
        "choices": {
            "A": "Store and validate passwords inside each application",
            "B": "Disable TLS because an identity provider replaces encryption",
            "C": "Trust an identity provider such as Microsoft Entra ID",
            "D": "Require Azure DDoS Protection before any sign-in can succeed",
        },
        "stem_style": "short_scenario",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask for identity-provider trust instead of correcting a passwords-in-each-app claim.",
    },
    "sc900_mlc_q283": {
        "stem": "Classification identified credit-card numbers in files. What is still required if those files must be encrypted?",
        "choices": {
            "A": "Nothing further; classification always encrypts matching files",
            "B": "Azure DDoS Protection",
            "C": "Protection controls such as sensitivity labels that act on the classified items",
            "D": "Deleting every file that contains a match",
        },
        "stem_style": "capability_selection",
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Ask the follow-on protection control without a learner-claim wrapper.",
    },
    "sc900_mlc_q296": {
        "choices": {
            "A": "Retention blocks outbound credit-card numbers as its primary job",
            "B": "DLP is the keep-or-delete lifecycle engine",
            "C": "Retention keeps content for the required period; DLP prevents risky sharing of sensitive information",
            "D": "Retention replaces eDiscovery; DLP replaces audit",
        },
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep the retention versus DLP pairing; replace Azure Bastion joke distractor with a neighboring wrong pairing.",
    },
    "sc900_mlc_q299": {
        "stem": "Which statement correctly describes Insider Risk Management compared with Conditional Access?",
        "choices": {
            "A": "Insider Risk Management is Microsoft's only MFA grant control",
            "B": "Conditional Access is a subset of Insider Risk Management file plans",
            "C": "Insider Risk Management analyzes internal user activity patterns; Conditional Access still evaluates sign-in conditions",
            "D": "Insider Risk Management issues FIDO2 keys and replaces Conditional Access",
        },
        "stem_style": "concept_distinction",
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Ask the IRM versus Conditional Access distinction without a replacement-claim wrapper.",
    },
    "sc900_mlc_q203": {
        "stem": "A user completes password and MFA challenges. The app then decides whether that account may open a finance report. Which process is the app performing?",
        "choices": {
            "A": "Authentication",
            "B": "Federation",
            "C": "Hashing",
            "D": "Authorization",
        },
        "stem_style": "distinction_comparison",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask for authorization after authentication instead of a two-sentence sequencing puzzle.",
    },
    "sc900_mlc_q206": {
        "stem": "Users connect to Microsoft 365 from home networks and coffee shops. Which model treats identity, not the corporate firewall, as a primary security perimeter?",
        "choices": {
            "A": "Zero Trust, with identity as a primary security perimeter",
            "B": "Castle-and-moat network trust for any HTTPS request",
            "C": "Defense in depth that treats the firewall as the only control",
            "D": "Shared responsibility that assigns all access decisions to the cloud provider",
        },
        "stem_style": "direct_concept",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask the identity-perimeter idea directly.",
    },
    "sc900_mlc_q223": {
        "stem": "Finance users must complete MFA from any network other than headquarters. Which Conditional Access signal supports that requirement?",
        "choices": {
            "A": "User risk from Identity Protection only, with no location condition",
            "B": "Device compliance as the only possible signal",
            "C": "Access reviews of the payroll group",
            "D": "Named or trusted network locations used as a condition in the policy",
        },
        "stem_style": "short_scenario",
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Keep one location-based Conditional Access decision.",
    },
    "sc900_mlc_q239": {
        "stem": "After a six-week project, owners should confirm whether remaining members still need a SharePoint group. Which Entra governance control is that recertification?",
        "choices": {
            "A": "Access reviews",
            "B": "Privileged Identity Management",
            "C": "Conditional Access",
            "D": "Temporary Access Pass",
        },
        "stem_style": "capability_selection",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask for access reviews without extra temporary-group story.",
    },
    "sc900_mlc_q241": {
        "stem": "Security wants Privileged Role Administrator to stay eligible until a person activates it. Which PIM idea is that?",
        "choices": {
            "A": "Permanent active assignments for all privileged roles",
            "B": "Access reviews as the only way to activate a role",
            "C": "Eligible assignments instead of standing active privileged assignments",
            "D": "Entitlement management as a replacement for role activation",
        },
        "stem_style": "direct_concept",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask eligible versus standing assignment directly.",
    },
    "sc900_mlc_q255": {
        "stem": "Defender for Cloud created recommendations after a security standard was assigned. What do those recommendations represent?",
        "choices": {
            "A": "Azure or multicloud resources that do not meet the assigned security standard",
            "B": "Purview Compliance Manager improvement actions",
            "C": "Entra access reviews of guest groups",
            "D": "Azure Bastion session logs",
        },
        "stem_style": "direct_concept",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 1,
        "reason": "Ask what Defender for Cloud recommendations are instead of diagnosing a Purview mix-up.",
    },
    "sc900_mlc_q278": {
        "stem": "Which statement correctly distinguishes Microsoft privacy principles from Purview Compliance Manager?",
        "choices": {
            "A": "Privacy principles are a Compliance Manager score formula",
            "B": "Privacy principles are Microsoft's data-handling commitments; Compliance Manager tracks customer improvement actions against assessments",
            "C": "Compliance Manager is Microsoft's public privacy statement",
            "D": "Both are Azure DDoS Protection SKUs",
        },
        "stem_style": "concept_distinction",
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Ask the privacy-principles versus Compliance Manager distinction without a sameness claim.",
    },
    "sc900_mlc_q282": {
        "stem": "What does a Microsoft Purview compliance score represent?",
        "choices": {
            "A": "An official Microsoft ISO certification for the customer",
            "B": "A replacement for the Service Trust Portal",
            "C": "Defender for Cloud secure score for Azure resources",
            "D": "Estimated remaining Compliance Manager improvement-action progress, not a certification",
        },
        "stem_style": "direct_concept",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 0,
        "reason": "Ask what compliance score is instead of correcting a certification misconception wrapper.",
    },
    "sc900_mlc_q267": {
        "stem": "Which statement correctly describes cloud security posture management compared with endpoint detection and response?",
        "choices": {
            "A": "CSPM is Microsoft's EDR agent and replaces Defender for Endpoint",
            "B": "CSPM assesses configuration posture; detecting running threats on a workload is cloud workload protection or endpoint detection",
            "C": "CSPM is only a retention label",
            "D": "CSPM issues FIDO2 keys to virtual machines",
        },
        "stem_style": "concept_distinction",
        "exam_calibration_tier": APPLIED,
        "reasoning_steps": 1,
        "reason": "Ask CSPM versus EDR directly.",
    },
    "sc900_mlc_q263": {
        "stem": "Which Microsoft capability synchronizes on-premises users into Microsoft Entra ID?",
        "choices": {
            "A": "Microsoft Defender for Identity",
            "B": "Microsoft Defender for Endpoint",
            "C": "Microsoft Entra Connect or related hybrid sync",
            "D": "Privileged Identity Management",
        },
        "stem_style": "capability_selection",
        "exam_calibration_tier": CORE,
        "reasoning_steps": 0,
        "reason": "Ask for Entra Connect instead of correcting a Defender for Identity mix-up.",
    },
}


def _choice_map(question: Mapping[str, Any]) -> dict[str, str]:
    return {str(key): str(value) for key, value in question["choices"].items()}


def _repair_choices(question: Mapping[str, Any], base_choices: dict[str, str]) -> dict[str, str]:
    leaf = str(question.get("blueprint_leaf_id") or "")
    neighbors = list(LEAF_NEIGHBORS.get(leaf, ()))
    correct = {str(item) for item in question.get("correct") or []}
    correct_text = " ".join(base_choices.get(letter, "") for letter in correct)
    used = {text.casefold() for text in base_choices.values()}
    pool = [item for item in neighbors if item.casefold() not in used]
    updated = dict(base_choices)
    for letter, text in base_choices.items():
        if letter in correct:
            continue
        label = classify_distractor(_prompt_or_rewrite(question), text, False, correct_text)
        if label in {"CROSS_PRODUCT_GIVEAWAY", "ABSURD"} and pool:
            replacement = pool.pop(0)
            updated[letter] = replacement
            used.add(replacement.casefold())
    return updated


def _prompt_or_rewrite(question: Mapping[str, Any]) -> str:
    rewrite = STEM_REWRITES.get(str(question.get("id") or ""), {})
    return str(rewrite.get("stem") or question.get("prompt") or "")


def _tier_for(question: Mapping[str, Any], difficulty: str, rewrite: Mapping[str, Any]) -> tuple[str, int, bool]:
    qid = str(question.get("id") or "")
    if rewrite.get("exam_calibration_tier") in {CORE, APPLIED, STRETCH}:
        steps = int(rewrite.get("reasoning_steps", 1))
        tier = str(rewrite["exam_calibration_tier"])
        return tier, steps, exam_simulation_eligible(tier)
    if qid in STRETCH_KEEP:
        return STRETCH, 2, False
    style = str(rewrite.get("stem_style") or question.get("stem_style") or "")
    if difficulty == "beginner" or style in DIRECT_STYLES:
        steps = 0 if style in {"direct_concept", "capability_selection", "service_selection", "current_topic"} else 1
        return CORE, steps, True
    return APPLIED, 1, True


def build_overlay_and_classification() -> dict[str, Any]:
    bank = load_json(COMPILED_BANK_PATH)
    difficulty_by_id = load_store_difficulty()
    overlay_items: list[dict[str, Any]] = []
    classification_items: list[dict[str, Any]] = []
    for question in bank["questions"]:
        qid = str(question["id"])
        rewrite = STEM_REWRITES.get(qid, {})
        difficulty = difficulty_by_id.get(qid, "")
        base_choices = _choice_map(question)
        if rewrite.get("choices"):
            merged = dict(base_choices)
            merged.update(rewrite["choices"])
            choices = merged
        elif str(question.get("question_type") or "") != "multi" and (
            str(question.get("stem_style") or "") == "misconception_correction" or qid in STRETCH_KEEP
        ):
            choices = _repair_choices(question, base_choices)
        else:
            giveaway_hits = 0
            correct = {str(item) for item in question.get("correct") or []}
            correct_text = " ".join(base_choices.get(letter, "") for letter in correct)
            for letter, text in base_choices.items():
                if letter in correct:
                    continue
                if classify_distractor(str(question.get("prompt") or ""), text, False, correct_text) in {
                    "CROSS_PRODUCT_GIVEAWAY",
                    "ABSURD",
                }:
                    giveaway_hits += 1
            if giveaway_hits >= 2 and str(question.get("stem_style") or "") in {
                "short_scenario",
                "concept_distinction",
                "distinction_comparison",
            }:
                choices = _repair_choices(question, base_choices)
            else:
                choices = base_choices
        changed_choices = choices != base_choices
        changed_stem = bool(rewrite.get("stem") and rewrite["stem"] != question.get("prompt"))
        changed_style = bool(rewrite.get("stem_style") and rewrite["stem_style"] != question.get("stem_style"))
        if changed_stem or changed_choices or changed_style:
            item: dict[str, Any] = {
                "question_id": qid,
                "reason": rewrite.get("reason")
                or (
                    "Replace cross-product or absurd distractors with neighboring SC-900 alternatives."
                    if changed_choices
                    else "Exam-style stem calibration."
                ),
                "preserve_identity": True,
                "tested_decision": question.get("tested_decision"),
            }
            if changed_stem:
                item["stem"] = rewrite["stem"]
            if changed_choices:
                item["choices"] = choices
            if rewrite.get("stem_style"):
                item["stem_style"] = rewrite["stem_style"]
            if rewrite.get("exam_calibration_tier"):
                item["exam_calibration_tier"] = rewrite["exam_calibration_tier"]
                item["reasoning_steps"] = int(rewrite.get("reasoning_steps", 1))
            overlay_items.append(item)
        tier, steps, eligible = _tier_for(question, difficulty, rewrite)
        classification_items.append(
            {
                "question_id": qid,
                "exam_calibration_tier": tier,
                "reasoning_steps": steps,
                "exam_simulation_eligible": eligible,
                "calibration_version": CALIBRATION_VERSION,
                "current_difficulty": difficulty,
                "stem_style": rewrite.get("stem_style") or question.get("stem_style") or "",
                "rewrite_applied": qid in {row["question_id"] for row in overlay_items if row["question_id"] == qid},
                "tested_decision": question.get("tested_decision"),
                "blueprint_leaf_id": question.get("blueprint_leaf_id"),
                "domain": question.get("domain"),
            }
        )
    overlay_payload = {
        "calibration_version": CALIBRATION_VERSION,
        "precalibration_bank_sha256": PRECALIBRATION_BANK_SHA256,
        "source_bank_sha256": sha256_file(COMPILED_BANK_PATH),
        "item_count": len(overlay_items),
        "items": overlay_items,
    }
    classification_payload = {
        "calibration_version": CALIBRATION_VERSION,
        "item_count": len(classification_items),
        "items": classification_items,
    }
    write_json(CALIBRATION_ROOT / "rewrite_overlay.json", overlay_payload)
    write_json(CALIBRATION_ROOT / "classification.json", classification_payload)
    return {
        "overlay_count": len(overlay_items),
        "classified": len(classification_items),
        "tier_counts": {
            CORE: sum(1 for row in classification_items if row["exam_calibration_tier"] == CORE),
            APPLIED: sum(1 for row in classification_items if row["exam_calibration_tier"] == APPLIED),
            STRETCH: sum(1 for row in classification_items if row["exam_calibration_tier"] == STRETCH),
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_overlay_and_classification(), indent=2))
