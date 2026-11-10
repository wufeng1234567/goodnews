/**
 * These string unions mirror backend/app/models/common.py exactly.
 * Keep both sides in sync when a new enum member is added.
 */
export type InputType = 'auto' | 'url' | 'text'

export type Verdict = 'true' | 'false' | 'partially_true' | 'insufficient_evidence'

export type GraphVerificationStatus = 'supported' | 'contradicted' | 'insufficient'

export type GraphMatchStatus = 'supported' | 'contradicted' | 'no_data'

export type EvidenceStance = 'supports' | 'refutes' | 'neutral'

export type NodeStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
