"""Fixed vocabularies shared by every agent, log line and UI element.

ITU-T Y.3172 pipeline nodes (as mapped to the smart-pen use case) and the
ITU AI Readiness dimensions named in the hackathon brief. Keep these in
sync with frontend/src/lib/types.ts and docs/y3172_mapping.md.
"""

from enum import StrEnum


class PipelineNode(StrEnum):
    SRC = "SRC"    # smart pen + writing board
    C = "C"        # school edge compute platform
    PP = "PP"      # pre-processing / harmonisation (device or edge)
    M = "M"        # models: anomaly detection, handwriting analysis
    P = "P"        # policy / human review (counsellor approval, overrides)
    D = "D"        # provider cloud analytics platform
    SINK = "SINK"  # parent / teacher mobile app


PIPELINE_NODE_LABELS: dict[PipelineNode, str] = {
    PipelineNode.SRC: "Smart pen & writing board",
    PipelineNode.C: "School edge compute platform",
    PipelineNode.PP: "Pre-processing / harmonisation",
    PipelineNode.M: "Models (anomaly detection, handwriting analysis)",
    PipelineNode.P: "Policy & human review (counsellor)",
    PipelineNode.D: "Provider cloud analytics platform",
    PipelineNode.SINK: "Parent / teacher mobile app",
}

PIPELINE_ORDER: list[PipelineNode] = list(PipelineNode)


class ReadinessDimension(StrEnum):
    OPEN_DATA_OSS = "open_data_open_source"
    GENAI_ECOSYSTEM = "generative_ai_content_ecosystem"
    CONTEXTUALISATION = "contextualisation_regional_development"
    DOMAIN_INTEGRATION = "domain_integration_cross_domain"
    HUMAN_SUPERVISION = "human_interaction_supervision"
    POLICY_IMPLEMENTATION = "ai_policy_implementation"
    SOCIAL_INCLUSION = "ai_social_inclusion"
    INFRA_ENERGY = "digital_infrastructure_energy"


READINESS_LABELS: dict[ReadinessDimension, str] = {
    ReadinessDimension.OPEN_DATA_OSS: "Open data and open-source management",
    ReadinessDimension.GENAI_ECOSYSTEM: "Generative AI content ecosystem",
    ReadinessDimension.CONTEXTUALISATION: "Contextualisation and regional development",
    ReadinessDimension.DOMAIN_INTEGRATION: "AI integration in domains and cross-domain analysis",
    ReadinessDimension.HUMAN_SUPERVISION: "Human interaction and supervision",
    ReadinessDimension.POLICY_IMPLEMENTATION: "AI policy and implementation opportunities",
    ReadinessDimension.SOCIAL_INCLUSION: "AI for social inclusion",
    ReadinessDimension.INFRA_ENERGY: "Digital infrastructure and energy",
}


class KBLayer(StrEnum):
    UAE_FEDERAL = "uae_federal"
    EMIRATE = "emirate"
    GLOBAL_EXAMPLE = "global_example"


class LegalStatus(StrEnum):
    IN_FORCE = "in_force"
    AMENDED = "amended"          # in force, but some articles amended
    REPEALED = "repealed"
    NOT_LEGISLATION = "not_legislation"  # strategies, guidelines, standards
    UNKNOWN = "unknown"


class AgentId(StrEnum):
    LEGAL_ADVISER = "legal_adviser"
    DATA_PROTECTION = "data_protection"
    EDUCATION = "education"
    CONSUMER_PROTECTION = "consumer_protection"
    AI_ETHICS = "ai_ethics"
    COORDINATOR = "coordinator"
    GAP_ANALYST = "gap_analyst"


class GapType(StrEnum):
    UNCLEAR_RESPONSIBILITY = "unclear_responsibility"
    MISSING_STANDARD = "missing_standard"
    LEGISLATIVE_GAP = "legislative_gap"
    COORDINATION_PROBLEM = "coordination_problem"
    OBJECTIVE_CONFLICT = "objective_conflict"


class Domain(StrEnum):
    CHILDREN_DATA = "children_data"
    CONSENT = "consent"
    EDUCATION = "education"
    IN_APP_PURCHASES = "in_app_purchases"
    ADVERTISING_MINORS = "advertising_minors"
    CROSS_BORDER = "cross_border_transfer"
    AUTOMATED_DECISIONS = "automated_decisions"
    DISABILITY_INCLUSION = "disability_inclusion"
    CYBERSECURITY = "cybersecurity"
    AI_ETHICS = "ai_ethics"
