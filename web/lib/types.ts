export type UserRole = "OWNER" | "ADMIN" | "RESEARCHER" | "VIEWER";

export interface User {
  id: number;
  email: string;
  role: UserRole;
  is_admin: boolean;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface Target {
  id: number;
  domain: string;
  company_id?: number | null;
  company_name?: string | null;
  program_source?: string | null;
  authorization_source?: string | null;
  scope?: string[] | null;
  scope_type?: string | null;
  notes?: string | null;
  authorization_record?: Record<string, unknown> | null;
  authorization_confirmed: boolean;
  monitoring_status: string;
  created_at: string;
  last_visited_at?: string | null;
  snapshots_count?: number;
  changes_count?: number;
}

export interface ResearchSignal {
  id: number;
  target_id: number;
  change_id?: number | null;
  cluster_id?: number | null;
  title: string;
  signal_type: string;
  summary: string;
  why_it_matters: string;
  recommended_research_area?: string | null;
  relevance_score: number;
  confidence_score: number;
  security_context_score: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;
  status: "new" | "interesting" | "investigating" | "saved" | "ignored" | "resolved" | string;
  historical_context?: Record<string, unknown> | null;
  affected_assets?: string[] | null;
  evidence_ids?: string[] | null;
  source_count: number;
  target_domain?: string | null;
  rationale?: string | null;
  description?: string | null;
  confidence?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ChangeCluster {
  id: number;
  target_id: number;
  title: string;
  summary: string;
  primary_category: string;
  affected_urls: string[];
  source_count: number;
  confidence: number;
  relevance_score: number;
  priority: string;
  created_at: string;
}

export interface ChangeEvidence {
  id: number;
  change_id: number;
  state: "before" | "current" | "diff";
  observation_id?: number | null;
  payload: Record<string, unknown>;
}

export interface Change {
  id: number;
  category: string;
  summary: string;
  security_relevance: number;
  confidence: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;
  source_url: string;
  detected_at: string;
  score_factors?: Record<string, unknown> | null;
  status?: "interesting" | "investigating" | "ignored" | "resolved" | string;
  target_id?: number;
  target_domain?: string | null;
  company_name?: string | null;
  researcher_note?: string;
  evidence?: ChangeEvidence[];
  affected_assets?: string[];
  related_features?: string[];
  related_technologies?: string[];
  historical_security_context?: string;
  ai_explanation?: string;
  before_state?: string | Record<string, unknown>;
  current_state?: string | Record<string, unknown>;
  diff_content?: string;
}

export interface Snapshot {
  id: number;
  collected_at: string;
  status: "pending" | "running" | "completed" | "failed" | string;
  error?: string | null;
  target_id?: number;
}

export interface TimelineEvent {
  id: number;
  event_type: string;
  title: string;
  summary: string;
  source: string;
  source_url?: string | null;
  observed_at: string;
  published_at?: string | null;
  confidence: number;
  relevance_score: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;
  company_id?: number | null;
  target_id?: number | null;
  provenance_category?: string | null;
  temporal_category?: string | null;
  quality_badge?: string | null;
  effective_at?: string | null;
  affected_asset_ids?: number[];
  technology_ids?: number[];
  evidence_ids?: number[];
  related_change_ids?: number[];
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface Note {
  id: number;
  title: string;
  body?: string | null;
  tags?: string[] | null;
  target_id?: number | null;
  linked_change_id?: number | null;
  linked_asset_id?: number | null;
  linked_evidence_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: number;
  title: string;
  description?: string | null;
  status: "open" | "in_progress" | "done" | string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  due_date?: string | null;
  target_id?: number | null;
  related_change_id?: number | null;
  created_at: string;
  updated_at?: string;
}

export interface Finding {
  id: number;
  title: string;
  description?: string | null;
  severity?: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;
  status: "draft" | "verified" | "reported" | "resolved" | string;
  target_id?: number | null;
  evidence_ids?: number[] | null;
  change_ids?: number[] | null;
  created_at: string;
}

export interface WatchlistEntry {
  id: number;
  entity_type: "target" | "change" | "asset" | "technology" | "cve" | string;
  entity_id: number;
  created_at: string;
  label?: string;
  description?: string;
  metadata?: Record<string, unknown>;
}

export interface Alert {
  id: number;
  alert_type: string;
  title: string;
  summary?: string | null;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;
  read: boolean;
  created_at: string;
}

export interface Profile {
  display_name?: string | null;
  username?: string | null;
  bio?: string | null;
  country?: string | null;
  timezone?: string | null;
  language?: string | null;
  researcher_type?: string | null;
  experience_level?: string | null;
  favorite_vuln_classes?: string[] | null;
  favorite_technologies?: string[] | null;
  public_profile?: boolean;
  handles?: Record<string, any> | null;
}

export interface ProviderHealth {
  name: string;
  status: "healthy" | "degraded" | "down" | "unconfigured" | string;
  error_summary?: string | null;
  recommended_fix?: string | null;
}

export interface SessionInfo {
  id: string | number;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
  last_active?: string | null;
  is_current?: boolean;
}

export interface UserSettings {
  appearance?: {
    theme?: "dark" | "system";
    density?: "compact" | "comfortable";
    mono_font?: boolean;
  };
  notifications?: {
    email_enabled?: boolean;
    digest_frequency?: "instant" | "daily" | "weekly";
    high_priority_only?: boolean;
  };
  research?: {
    default_relevance_threshold?: number;
    auto_bookmark_high_risk?: boolean;
    cve_correlation_enabled?: boolean;
  };
  privacy?: {
    public_profile?: boolean;
    allow_leaderboard?: boolean;
    telemetry?: boolean;
  };
}

export interface SearchResultItem {
  id: number | string;
  type: "target" | "change" | "asset" | "feature" | "note" | "finding";
  title: string;
  subtitle?: string;
  url: string;
  badge?: string;
  date?: string;
}

export interface SearchResults {
  targets?: SearchResultItem[];
  changes?: SearchResultItem[];
  assets?: SearchResultItem[];
  features?: SearchResultItem[];
  notes?: SearchResultItem[];
  findings?: SearchResultItem[];
}

export type ScopeStatus = "IN_SCOPE" | "RELATED" | "OUT_OF_SCOPE" | "UNKNOWN" | "PENDING_VERIFICATION";
export type VerificationStatus = "VERIFIED" | "PARTIALLY_VERIFIED" | "UNVERIFIED" | "STALE";

export interface ProgramScopeRule {
  id: number;
  pattern: string;
  inclusion_type: "INCLUDE" | "EXCLUDE" | "CONDITIONAL" | "UNKNOWN";
  asset_type?: string | null;
  confidence: number;
  source_url?: string | null;
  evidence?: string | null;
  last_verified_at?: string | null;
}

export interface SecurityProgram {
  id: number;
  company_id?: number;
  company_name?: string;
  company_domain?: string;
  company_website?: string | null;
  platform: string;
  program_name?: string | null;
  program_handle?: string | null;
  program_type?: string;
  status?: string;
  program_url?: string | null;
  policy_url?: string | null;
  source_url?: string | null;
  is_public?: boolean;
  offers_bounties?: boolean;
  min_bounty?: number | null;
  max_bounty?: number | null;
  currency?: string;
  submission_state?: string;
  scope_summary?: string | null;
  discovered_at?: string;
  last_verified_at?: string | null;
  scope_rules_count?: number;
  rules?: ProgramScopeRule[];
  rules_count?: number;
}

export interface AssetEvidence {
  source_type: string;
  source_url: string;
  evidence_text: string;
  confidence: number;
  observed_at?: string;
}

export interface CompanyAsset {
  id: number;
  name: string;
  hostname: string;
  asset_type: string;
  url?: string | null;
  scope_status: ScopeStatus;
  verification_status: VerificationStatus;
  confidence: number;
  source: string;
  discovered_at?: string;
  last_seen_at?: string;
  evidence?: AssetEvidence[];
}

export interface Product {
  id: number;
  name: string;
  description?: string | null;
  status: string;
  confidence: number;
  domain_ids?: number[];
  first_seen_at?: string;
  last_seen_at?: string;
}

export interface CompanyFeature {
  id: number;
  name: string;
  category?: string | null;
  description?: string | null;
  confidence: number;
  product_id?: number | null;
  asset_id?: number | null;
  first_observed?: string;
  last_observed?: string;
}

export interface CompanyApi {
  id: number;
  method: string;
  path: string;
  version?: string | null;
  auth_requirement?: string | null;
  source: string;
  confidence: number;
  first_seen?: string;
  last_seen?: string;
}

export interface Company {
  id: number;
  name: string;
  canonical_domain: string;
  legal_name?: string | null;
  industry?: string | null;
  country?: string | null;
  description?: string | null;
  website_url?: string | null;
  security_policy_url?: string | null;
  bug_bounty_url?: string | null;
  disclosure_policy_url?: string | null;
  source_confidence: number;
  last_enriched_at?: string | null;
  created_at: string;
  assets_count?: number;
  in_scope_assets_count?: number;
  products_count?: number;
  signals_count?: number;
  programs_count?: number;
  metrics?: {
    total_assets: number;
    in_scope_assets: number;
    related_assets: number;
    out_of_scope_assets: number;
    unknown_assets: number;
    products_count: number;
    signals_count: number;
  };
  security_programs?: SecurityProgram[];
  top_signals?: ResearchSignal[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  scope: string;
  confidence: number;
  verification_status?: string;
  canonical_domain?: string;
  priority?: string;
  relevance_score?: number;
  details?: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface AttackSurfaceGraph {
  company: {
    id: number;
    name: string;
    canonical_domain: string;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    assets_count: number;
    products_count: number;
    apis_count: number;
    features_count: number;
    signals_count: number;
  };
}

export interface HistoricalCoverage {
  id?: number;
  company_id: number;
  canonical_domain?: string;
  coverage_start?: string | null;
  coverage_end?: string | null;
  confidence: number;
  sources_count: number;
  confirmed_events_count: number;
  estimated_events_count: number;
  partial_periods?: string[] | null;
  last_synced_at?: string | null;
  notes?: string | null;
  disclaimer?: string;
}

export interface HistoricalRelease {
  id: number;
  version?: string | null;
  tag: string;
  title?: string | null;
  body?: string | null;
  published_at?: string | null;
  source_url?: string | null;
  confidence: number;
  semantic_changes?: string[] | null;
}

export interface HistoryComparisonResult {
  period: {
    from: string;
    to: string;
  };
  added_assets: Array<{ id: number; hostname: string; type: string; scope: string; first_observed: string }>;
  added_features: Array<{ id: number; name: string; category?: string; first_observed: string }>;
  added_apis: Array<{ id: number; method: string; path: string; first_seen: string }>;
  security_events: Array<{ id: number; cve_id?: string; vulnerability_class?: string; severity?: string; published?: string }>;
  releases: Array<{ id: number; tag: string; title?: string; published_at?: string; semantic_changes?: string[] }>;
  summary: {
    assets_count: number;
    features_count: number;
    apis_count: number;
    security_events_count: number;
    releases_count: number;
  };
}

export interface CompanySource {
  id: number;
  company_id: number;
  company_name?: string;
  name: string;
  source_url: string;
  source_type: string;
  authority_level: string;
  product_scope?: string | null;
  platform_scope?: string | null;
  parser_strategy: string;
  collection_method: string;
  feed_url?: string | null;
  api_url?: string | null;
  poll_interval_seconds: number;
  priority: string;
  enabled: boolean;
  status: string;
  health_state: "HEALTHY" | "DEGRADED" | "FAILED" | "DISABLED" | string;
  last_checked_at?: string | null;
  last_changed_at?: string | null;
  consecutive_failures: number;
  parser_version: string;
  notes?: string | null;
}

export interface CompanyCoverage {
  overall_coverage_pct: number;
  tracking_status: "TRACKING" | "PARTIAL" | "DEGRADED" | "INITIALIZING" | string;
  sources_count: number;
  healthy_sources: number;
  official_coverage: number;
  developer_coverage: number;
  security_coverage: number;
  infrastructure_coverage: number;
  technographic_coverage: number;
  freshness_score: number;
  disclaimer?: string;
}

export interface SourceRun {
  id: number;
  started_at: string;
  finished_at?: string | null;
  status: string;
  http_status?: number | null;
  items_found: number;
  items_changed: number;
  duration_ms: number;
  error_message?: string | null;
  credits_used: number;
  response_bytes: number;
}

export interface ProviderMetadata {
  provider_id: string;
  name: string;
  official_docs_url: string;
  method: string;
  auth_type: string;
  license_required: boolean;
  commercial_allowed: boolean;
  rate_limit_per_min: number;
  change_capable: boolean;
  historical_capable: boolean;
  notes: string;
  status?: string;
  health?: {
    status: string;
    error_summary?: string | null;
    recommended_fix?: string | null;
    last_checked?: string;
  };
}

export interface ProviderUsage {
  requests: number;
  credits: number;
  bytes: number;
  errors: number;
  estimated_cost: number;
}

export interface SecurityIntelligenceEvent {
  id: number;
  title: string;
  summary: string;
  event_type: string;
  published_at: string;
  updated_at?: string | null;
  source_url: string;
  source_name: string;
  additional_sources: string[];
  cve_ids: string[];
  cwe_ids: string[];
  affected_products: string[];
  affected_companies: string[];
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN" | string;
  actively_exploited: boolean;
  known_exploitation_evidence?: string | null;
  security_relevance?: string | null;
  confidence: number;
  fingerprint: string;
  severity_score: number;
  freshness_score: number;
  exploitation_score: number;
  relevance_score: number;
  priority_score: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
  grounding_metadata?: {
    web_search_queries?: string[];
    grounding_chunks_count?: number;
    [key: string]: unknown;
  };
  correlated_company_ids: number[];
  correlated_product_ids: number[];
  correlated_technology_ids: number[];
  correlated_advisory_ids: number[];
  correlated_companies?: Array<{ id: number; name: string; domain?: string }>;
  correlated_products?: Array<{ id: number; name: string }>;
  correlated_technologies?: Array<{ id: number; name: string }>;
  correlated_advisories?: Array<{ id: number; cve_id: string; title: string }>;
  created_at: string;
}

export interface SecurityIntelligenceStats {
  total_events: number;
  actively_exploited_count: number;
  by_severity: Record<string, number>;
  by_priority: Record<string, number>;
  by_event_type: Record<string, number>;
}

export interface LiveIntelligenceEvent {
  id: string;
  raw_id: number;
  kind: "SIGNAL" | "CHANGE" | "ASSET";
  event_type: "NEW ASSET" | "SCOPE CHANGE" | "API CHANGE" | "TECHNOLOGY CHANGE" | "SECURITY EVENT" | "RESEARCH SIGNAL";
  target: string;
  target_id?: number | null;
  company: string;
  company_id?: number | null;
  what_changed: string;
  why_it_matters?: string;
  timestamp: string | null;
  security_relevance: number;
  confidence: number;
  priority: string;
  status: string;
  source: string;
  evidence: string[];
}

export interface LiveTrialStatus {
  trial_run_id?: number;
  status: string;
  started_at: string;
  runtime_seconds: number;
  runtime_formatted: string;
  window_hours: number;
  targets: number;
  targets_monitored: number;
  companies_tracked?: number;
  collection_cycles: number;
  collection_runs: number;
  success: number;
  successful_runs: number;
  failed: number;
  failed_runs: number;
  assets_discovered: number;
  real_changes: number;
  changes_detected: number;
  changes_today: number;
  security_correlations: number;
  research_signals: number;
  signals_today: number;
  high_value_findings: number;
  high_value_signals: number;
  evidence_records: number;
  last_successful_collection?: string | null;
  latest_event_timestamp?: string | null;
}

export interface BillingPlan {
  id: string;
  tier: "FREE" | "RESEARCHER" | "PRO" | "ADVANCED" | string;
  name: string;
  price_inr: number;
  monthly_price_inr: number;
  yearly_price_inr?: number;
  savings_inr?: number;
  currency: string;
  billing_period: string;
  active: boolean;
  features: string[];
  limits: {
    max_targets: number;
    export_formats: string[];
    max_export_rows: number;
    research_limits?: string;
  };
}

export interface SubscriptionInfo {
  id: number;
  tier: string;
  status: string;
  provider: string;
  is_verified_payment: boolean;
  current_period_start?: string | null;
  current_period_end?: string | null;
  cancel_at_period_end: boolean;
  plan: BillingPlan;
}

export interface PaymentTransactionItem {
  id: number;
  order_id: string;
  payment_id?: string | null;
  plan_tier: string;
  billing_interval: string;
  amount_inr: number;
  expected_amount_paisa: number;
  currency: string;
  status: string;
  payment_state: string;
  gateway_status?: string | null;
  environment: string;
  receipt?: string | null;
  failure_reason?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
}

