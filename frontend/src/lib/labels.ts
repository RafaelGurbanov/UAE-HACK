import type { MessageKey } from '../i18n';
import type { KBLayer, LegalStatus, PipelineNode, ReadinessDimension } from './types';

export const PIPELINE: PipelineNode[] = ['SRC', 'C', 'PP', 'M', 'P', 'D', 'SINK'];

/** Readiness dimensions most relevant per node (docs/y3172_mapping.md). */
export const NODE_DIMENSIONS: Record<PipelineNode, ReadinessDimension[]> = {
  SRC: ['human_interaction_supervision', 'ai_social_inclusion'],
  C: ['digital_infrastructure_energy'],
  PP: ['open_data_open_source'],
  M: ['contextualisation_regional_development', 'domain_integration_cross_domain'],
  P: ['human_interaction_supervision', 'ai_policy_implementation'],
  D: ['digital_infrastructure_energy', 'ai_policy_implementation'],
  SINK: ['ai_social_inclusion', 'generative_ai_content_ecosystem'],
};

export const nodeKey = (n: PipelineNode) => `node.${n}` as MessageKey;
export const nodeShortKey = (n: PipelineNode) => `nodeShort.${n}` as MessageKey;
export const dimKey = (d: ReadinessDimension) => `dim.${d}` as MessageKey;
export const layerKey = (l: KBLayer) => `layer.${l}` as MessageKey;
export const legalKey = (s: LegalStatus) => `legal.${s}` as MessageKey;
