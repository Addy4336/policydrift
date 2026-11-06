// Types mirror the FastAPI contract in api/ (see web/README.md).

export type Language = "en" | "hi" | "gu";

export const LANGUAGES: readonly Language[] = ["en", "hi", "gu"] as const;

export interface AskRequest {
  question: string;
  language: Language;
  /** ISO date, YYYY-MM-DD. Defaults to today on the server. */
  as_of?: string;
}

export interface Citation {
  id: number;
  chunk_id: string;
  scheme: string;
  scheme_name: string;
  version: string;
  effective_from: string | null;
  effective_to: string | null;
  in_force: boolean;
  title: string;
  source_url: string;
  posted_on: string;
  ministry: string;
  excerpt: string;
}

export interface RuleVersion {
  scheme: string;
  scheme_name: string;
  version: string;
  effective_from: string | null;
  effective_to: string | null;
}

export interface Conflict {
  scheme: string;
  scheme_name: string;
  superseded_version: string;
  effective_from: string | null;
  effective_to: string | null;
  title: string;
  source_url: string;
  excerpt: string;
  note: string;
}

export interface NumberCheck {
  value: string;
  verified: boolean;
  cited_in: number[];
}

export interface Checks {
  citations_valid: boolean;
  uncited: boolean;
  invalid_markers: number[];
  numbers: NumberCheck[];
}

export interface AskResponse {
  answer: string;
  language: Language;
  as_of: string;
  model: string;
  cached: boolean;
  latency_ms: number;
  citations: Citation[];
  rule_versions: RuleVersion[];
  conflicts: Conflict[];
  checks: Checks;
  warnings: string[];
  declined?: boolean;
  search_query?: string;
}

export interface SchemeVersion {
  id: string;
  effective_from: string | null;
  effective_to: string | null;
  announced_on: string | null;
  in_force: boolean;
}

export interface Scheme {
  id: string;
  name: string;
  versions: SchemeVersion[];
}

export type Examples = Record<Language, string[]>;

export interface Results {
  dev: string;
  test: string | null;
}

export interface Health {
  status: "ok";
  chunks: number;
  model: string;
}
