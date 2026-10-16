// Mirrors backend/src/cv_eval/schemas.py

export type EvidenceLevel = "supported" | "partial" | "missing";
export type Importance = "must_have" | "nice_to_have";
export type Rating = "strong" | "adequate" | "weak";

export interface Passage {
  id: string;
  section: string | null;
  kind: "paragraph" | "bullet" | "table_row";
  text: string;
}

export interface Requirement {
  id: string;
  text: string;
  category: string;
  importance: Importance;
  jd_quote: string;
}

export interface RequirementFit {
  requirement: Requirement;
  level: EvidenceLevel;
  evidence: Passage[];
  rationale: string;
  suggestion: string | null;
}

export interface LevelCounts {
  supported: number;
  partial: number;
  missing: number;
}

export interface FitScore {
  score: number;
  band: string;
  must_have: LevelCounts;
  nice_to_have: LevelCounts;
  rubric: string;
}

export interface DimensionFeedback {
  dimension: "clarity" | "relevance" | "specificity" | "achievements";
  rating: Rating;
  comment: string;
  passage_ids: string[];
}

export interface BulletRewrite {
  passage_id: string;
  issue: string;
  rewritten: string;
  rationale: string;
}

export interface Priority {
  title: string;
  detail: string;
  requirement_ids: string[];
  passage_ids: string[];
}

export interface Feedback {
  quality: DimensionFeedback[];
  summary: { text: string; rationale: string };
  rewrites: BulletRewrite[];
  priorities: Priority[];
}

export interface StageMeta {
  name: string;
  seconds: number;
  requests: number;
  input_tokens: number;
  output_tokens: number;
}

export interface Report {
  cv_filename: string;
  requirements: RequirementFit[];
  score: FitScore;
  feedback: Feedback;
  passages: Passage[];
  meta: { model: string; matcher: string; stages: StageMeta[] };
}

export type Stage = "upload" | "requirements" | "matching" | "feedback";

export type StreamEvent =
  | { type: "stage"; stage: Exclude<Stage, "upload"> }
  | { type: "report"; report: Report }
  | { type: "error"; message: string };
