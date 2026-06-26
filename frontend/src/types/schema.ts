export interface FieldInfo {
  name: string;
  data_type: string;
  nullable: boolean;
  primary_key: boolean;
  unique: boolean;
  default_value: string | null;
  foreign_key_target: string | null;
  indexed: boolean;
  index_names: string[];
}

export interface Index {
  name: string;
  columns: string[];
  unique: boolean;
}

export interface EntityInfo {
  name: string;
  entity_type: "table" | "view" | "collection";
  fields: FieldInfo[];
  indexes: Index[];
  row_count: number | null;
}

export interface RelationshipInfo {
  source_entity: string;
  source_field: string;
  target_entity: string;
  target_field: string;
  declared: boolean;
  confidence: number;
  evidence: string[];
  relationship_type: string;
}

export type Severity = "high" | "medium" | "low" | "information";
export type ReviewStatus = "open" | "accepted" | "ignored";

export interface Finding {
  rule_id: string;
  database_type: string;
  entity: string;
  field: string | null;
  severity: Severity;
  confidence: number | null;
  title: string;
  description: string;
  evidence: string[];
  impact: string;
  recommendation: string;
  suggested_command: string | null;
  review_status: ReviewStatus;
}

export interface AnalysisMetadata {
  source_type: string;
  source_name: string;
  analysed_at: string;
  entity_count: number;
  relationship_count: number;
  finding_count: number;
  warning_count: number;
  generator: string;
  note: string;
}

export interface AnalysisResult {
  analysis_metadata: AnalysisMetadata;
  entities: EntityInfo[];
  relationships: RelationshipInfo[];
  findings: Finding[];
  warnings: string[];
}

export interface MySQLParams {
  host: string;
  database: string;
  username: string;
  password: string;
  port: number;
  ssl: boolean;
  timeout: number;
}

export interface ConnectResponse {
  session_id: string;
  source_name: string;
  source_type: string;
  message: string;
}
