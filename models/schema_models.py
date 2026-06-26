from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldInfo:
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default_value: str | None = None
    foreign_key_target: str | None = None  # "table.column"
    indexed: bool = False
    index_names: list[str] = field(default_factory=list)
    occurrence_rate: float | None = None   # MongoDB only
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityInfo:
    name: str
    entity_type: str  # "table" | "view" | "collection"
    fields: list[FieldInfo]
    indexes: list[dict[str, Any]] = field(default_factory=list)
    row_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipInfo:
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    declared: bool          # True = FK constraint; False = inferred
    confidence: float       # 1.0 for declared, 0.0–1.0 for inferred
    evidence: list[str] = field(default_factory=list)
    relationship_type: str | None = None  # e.g. "many-to-one"


@dataclass
class Finding:
    rule_id: str
    database_type: str      # "sqlite" | "mysql" | "mongodb"
    entity: str
    severity: str           # "high" | "medium" | "low" | "information"
    title: str
    description: str
    evidence: list[str]
    impact: str
    recommendation: str
    field: str | None = None
    confidence: float | None = None
    suggested_command: str | None = None
    review_status: str = "open"  # "open" | "accepted" | "ignored"


@dataclass
class AnalysisResult:
    source_type: str        # "sqlite" | "mysql" | "mongodb"
    source_name: str
    analysed_at: str        # ISO-8601 timestamp
    entities: list[EntityInfo]
    relationships: list[RelationshipInfo]
    findings: list[Finding]
    warnings: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
