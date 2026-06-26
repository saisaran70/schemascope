"""Tests for exporters/ — Step 7.

Covers markdown_exporter.py and json_exporter.py.
All tests use in-memory AnalysisResult objects — no file I/O or DB connections.
"""
from __future__ import annotations

import json

import pytest

from exporters.json_exporter import export_json, export_json_dict
from exporters.markdown_exporter import export_markdown, generate_export_filename
from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    Finding,
    RelationshipInfo,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _field(
    name: str,
    data_type: str = "integer",
    *,
    primary_key: bool = False,
    foreign_key_target: str | None = None,
    nullable: bool = True,
    unique: bool = False,
    indexed: bool = False,
    default_value: str | None = None,
) -> FieldInfo:
    return FieldInfo(
        name=name, data_type=data_type,
        primary_key=primary_key, foreign_key_target=foreign_key_target,
        nullable=nullable, unique=unique, indexed=indexed,
        default_value=default_value,
    )


def _table(name: str, fields: list[FieldInfo], indexes: list[dict] | None = None) -> EntityInfo:
    return EntityInfo(name=name, entity_type="table", fields=fields, indexes=indexes or [])


def _view(name: str, fields: list[FieldInfo] | None = None) -> EntityInfo:
    return EntityInfo(name=name, entity_type="view", fields=fields or [])


def _rel(src: str, sf: str, tgt: str, tf: str,
         declared: bool = True, confidence: float = 1.0,
         evidence: list[str] | None = None) -> RelationshipInfo:
    return RelationshipInfo(
        source_entity=src, source_field=sf,
        target_entity=tgt, target_field=tf,
        declared=declared, confidence=confidence,
        evidence=evidence or (["FK constraint"] if declared else ["name match"]),
    )


def _finding(
    rule_id: str = "SQL-001",
    entity: str = "logs",
    severity: str = "medium",
    field: str | None = None,
    suggested_command: str | None = None,
    review_status: str = "open",
    confidence: float | None = None,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        database_type="sqlite",
        entity=entity,
        field=field,
        severity=severity,
        confidence=confidence,
        title=f"Test finding {rule_id}",
        description=f"Description for {rule_id}.",
        evidence=["evidence item 1", "evidence item 2"],
        impact="Some impact.",
        recommendation="Some recommendation.",
        suggested_command=suggested_command,
        review_status=review_status,
    )


def _result(
    entities: list[EntityInfo] | None = None,
    relationships: list[RelationshipInfo] | None = None,
    findings: list[Finding] | None = None,
    warnings: list[str] | None = None,
    source_name: str = "test.db",
    source_type: str = "sqlite",
    metadata: dict | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        source_type=source_type,
        source_name=source_name,
        analysed_at="2026-06-26T14:00:00+00:00",
        entities=entities or [],
        relationships=relationships or [],
        findings=findings or [],
        warnings=warnings or [],
        metadata=metadata or {},
    )


# ===========================================================================
# MARKDOWN EXPORTER
# ===========================================================================

class TestMarkdownHeader:
    def test_starts_with_h1(self):
        out = export_markdown(_result())
        assert out.startswith("# SchemaScope Analysis Report")

    def test_contains_source_name(self):
        out = export_markdown(_result(source_name="mydb.sqlite"))
        assert "mydb.sqlite" in out

    def test_contains_source_type_uppercase(self):
        out = export_markdown(_result(source_type="sqlite"))
        assert "SQLITE" in out

    def test_contains_analysed_at(self):
        out = export_markdown(_result())
        assert "2026-06-26" in out

    def test_read_only_notice_present(self):
        out = export_markdown(_result())
        assert "read-only" in out.lower() or "manual review" in out.lower()


class TestMarkdownSummary:
    def test_analysis_summary_heading(self):
        out = export_markdown(_result())
        assert "## Analysis Summary" in out

    def test_table_count_shown(self):
        out = export_markdown(_result(entities=[
            _table("users", [_field("id", primary_key=True)]),
        ]))
        assert "Tables" in out
        assert "1" in out

    def test_view_count_shown(self):
        out = export_markdown(_result(entities=[
            _view("vw_users", [_field("id")]),
        ]))
        assert "Views" in out

    def test_finding_counts_by_severity(self):
        findings = [
            _finding("SQL-001", severity="high"),
            _finding("SQL-002", severity="medium"),
            _finding("SQL-003", severity="low"),
        ]
        out = export_markdown(_result(findings=findings))
        assert "High" in out
        assert "Medium" in out
        assert "Low" in out

    def test_confirmed_relationship_count(self):
        out = export_markdown(_result(
            relationships=[_rel("orders", "cid", "customers", "id")]
        ))
        assert "Confirmed" in out


class TestMarkdownWarnings:
    def test_no_warnings_section_when_empty(self):
        out = export_markdown(_result())
        assert "Limitations and Warnings" not in out

    def test_warnings_section_present_when_non_empty(self):
        out = export_markdown(_result(warnings=["View vw_x could not be inspected."]))
        assert "Limitations and Warnings" in out

    def test_warning_text_shown(self):
        out = export_markdown(_result(warnings=["Something went wrong."]))
        assert "Something went wrong." in out

    def test_multiple_warnings_all_shown(self):
        out = export_markdown(_result(warnings=["W1", "W2", "W3"]))
        assert "W1" in out
        assert "W2" in out
        assert "W3" in out


class TestMarkdownEntities:
    def test_entities_heading(self):
        out = export_markdown(_result(entities=[_table("t", [_field("id")])]))
        assert "## Entities" in out

    def test_entity_name_in_h3(self):
        out = export_markdown(_result(entities=[_table("customers", [_field("id")])]))
        assert "### customers" in out

    def test_field_name_in_table(self):
        out = export_markdown(_result(entities=[
            _table("users", [_field("id", primary_key=True), _field("name", "text")])
        ]))
        assert "id" in out
        assert "name" in out

    def test_pk_marker_shown(self):
        out = export_markdown(_result(entities=[
            _table("users", [_field("id", "integer", primary_key=True)])
        ]))
        assert "✓" in out  # PK checkmark

    def test_fk_target_shown(self):
        out = export_markdown(_result(entities=[
            _table("orders", [_field("customer_id", foreign_key_target="customers.id")])
        ]))
        assert "customers.id" in out

    def test_view_label_shown(self):
        out = export_markdown(_result(entities=[_view("vw_orders")]))
        assert "View" in out

    def test_index_info_shown(self):
        out = export_markdown(_result(entities=[
            _table("orders", [_field("id", primary_key=True)],
                   indexes=[{"name": "idx_status", "columns": ["status"], "unique": False}])
        ]))
        assert "idx_status" in out

    def test_default_value_shown(self):
        out = export_markdown(_result(entities=[
            _table("settings", [_field("flag", "integer", default_value="1")])
        ]))
        assert "1" in out

    def test_no_entities_message(self):
        out = export_markdown(_result(entities=[]))
        assert "No entities found" in out or "Entities" in out


class TestMarkdownRelationships:
    def test_confirmed_relationships_heading(self):
        out = export_markdown(_result())
        assert "## Confirmed Relationships" in out

    def test_inferred_relationships_heading(self):
        out = export_markdown(_result())
        assert "## Inferred Relationships" in out

    def test_declared_rel_shown(self):
        out = export_markdown(_result(
            relationships=[_rel("orders", "customer_id", "customers", "id")]
        ))
        assert "orders" in out
        assert "customer_id" in out
        assert "customers" in out

    def test_inferred_rel_shown_with_confidence(self):
        out = export_markdown(_result(
            relationships=[_rel("orders", "customer_id", "customers", "id",
                                declared=False, confidence=0.75)]
        ))
        assert "75%" in out

    def test_no_declared_shows_placeholder(self):
        out = export_markdown(_result(relationships=[]))
        assert "No confirmed relationships" in out

    def test_no_inferred_shows_placeholder(self):
        out = export_markdown(_result(relationships=[]))
        assert "No inferred relationships" in out


class TestMarkdownRecommendations:
    def test_recommendations_heading(self):
        out = export_markdown(_result())
        assert "## Recommendations" in out

    def test_no_findings_shows_placeholder(self):
        out = export_markdown(_result(findings=[]))
        assert "No findings" in out

    def test_finding_rule_id_shown(self):
        out = export_markdown(_result(findings=[_finding("SQL-003")]))
        assert "SQL-003" in out

    def test_finding_severity_shown(self):
        out = export_markdown(_result(findings=[_finding(severity="high")]))
        assert "High" in out

    def test_finding_description_shown(self):
        out = export_markdown(_result(findings=[_finding("SQL-001")]))
        assert "Description for SQL-001" in out

    def test_finding_evidence_shown(self):
        out = export_markdown(_result(findings=[_finding("SQL-001")]))
        assert "evidence item 1" in out

    def test_finding_impact_shown(self):
        out = export_markdown(_result(findings=[_finding("SQL-001")]))
        assert "Some impact" in out

    def test_finding_recommendation_shown(self):
        out = export_markdown(_result(findings=[_finding("SQL-001")]))
        assert "Some recommendation" in out

    def test_findings_grouped_by_severity(self):
        findings = [
            _finding("SQL-001", severity="high"),
            _finding("SQL-002", severity="low"),
            _finding("SQL-003", severity="medium"),
        ]
        out = export_markdown(_result(findings=findings))
        high_pos = out.index("### High")
        medium_pos = out.index("### Medium")
        low_pos = out.index("### Low")
        assert high_pos < medium_pos < low_pos

    def test_accepted_finding_review_status_shown(self):
        out = export_markdown(_result(findings=[_finding(review_status="accepted")]))
        assert "Accepted" in out or "accepted" in out

    def test_confidence_shown_when_present(self):
        out = export_markdown(_result(findings=[_finding(confidence=0.75)]))
        assert "75%" in out

    def test_field_shown_in_finding_when_present(self):
        out = export_markdown(_result(findings=[_finding("SQL-002", field="customer_id")]))
        assert "customer_id" in out


class TestMarkdownSuggestedCommands:
    def test_commands_section_absent_when_no_commands(self):
        out = export_markdown(_result(findings=[_finding()]))
        assert "## Suggested Commands" not in out

    def test_commands_section_present_when_commands_exist(self):
        out = export_markdown(_result(
            findings=[_finding(suggested_command="CREATE INDEX idx ON t(col);")]
        ))
        assert "## Suggested Commands" in out

    def test_command_text_shown(self):
        cmd = "CREATE INDEX idx ON orders(customer_id);"
        out = export_markdown(_result(
            findings=[_finding(suggested_command=cmd)]
        ))
        assert cmd in out

    def test_review_only_warning_in_commands_section(self):
        out = export_markdown(_result(
            findings=[_finding(suggested_command="ALTER TABLE t ADD COLUMN x TEXT;")]
        ))
        assert "review only" in out.lower() or "backup" in out.lower()

    def test_command_in_code_block(self):
        out = export_markdown(_result(
            findings=[_finding(suggested_command="SELECT 1;")]
        ))
        assert "```" in out


class TestMarkdownMetadata:
    def test_metadata_section_present(self):
        out = export_markdown(_result())
        assert "## Analysis Metadata" in out

    def test_source_type_in_metadata(self):
        out = export_markdown(_result(source_type="mysql"))
        assert "mysql" in out

    def test_analysed_at_in_metadata(self):
        out = export_markdown(_result())
        assert "2026-06-26" in out

    def test_extra_metadata_shown(self):
        out = export_markdown(_result(metadata={"sample_size": 100}))
        assert "sample_size" in out or "100" in out


class TestMarkdownSecurity:
    def test_no_raw_password_in_output(self):
        result = _result(metadata={"password": "topsecret"})
        out = export_markdown(result)
        # password key should not leak into markdown (metadata blocked)
        # The value shouldn't appear
        assert "topsecret" not in out

    def test_source_name_shown_not_full_path(self):
        # Source name is whatever was passed in — we trust caller sanitised it
        out = export_markdown(_result(source_name="test.db"))
        assert "test.db" in out


# ===========================================================================
# generate_export_filename
# ===========================================================================

class TestGenerateExportFilename:
    def test_starts_with_schemascope(self):
        fn = generate_export_filename("mydb.sqlite", "20260626T140000", "report.md")
        assert fn.startswith("schemascope_")

    def test_ends_with_suffix(self):
        fn = generate_export_filename("mydb", "20260626T140000", "report.md")
        assert fn.endswith("report.md")

    def test_source_name_included(self):
        fn = generate_export_filename("production_db.sqlite", "20260626T140000", "analysis.json")
        assert "production_db" in fn

    def test_extension_stripped_from_source(self):
        fn = generate_export_filename("mydb.sqlite", "20260626T140000", "report.md")
        assert ".sqlite" not in fn.replace("report.md", "")

    def test_special_chars_in_source_replaced(self):
        fn = generate_export_filename("my db (1).sqlite", "20260626T140000", "report.md")
        assert " " not in fn
        assert "(" not in fn

    def test_json_suffix(self):
        fn = generate_export_filename("db", "20260626T140000", "analysis.json")
        assert fn.endswith("analysis.json")

    def test_mmd_suffix(self):
        fn = generate_export_filename("db", "20260626T140000", "diagram.mmd")
        assert fn.endswith("diagram.mmd")

    def test_timestamp_included(self):
        fn = generate_export_filename("db", "20260626T140000Z", "report.md")
        assert "20260626" in fn


# ===========================================================================
# JSON EXPORTER
# ===========================================================================

class TestJsonExportStructure:
    def test_returns_valid_json_string(self):
        out = export_json(_result())
        parsed = json.loads(out)
        assert isinstance(parsed, dict)

    def test_top_level_keys_present(self):
        out = export_json(_result())
        parsed = json.loads(out)
        for key in ("analysis_metadata", "entities", "relationships", "findings", "warnings"):
            assert key in parsed, f"Missing key: {key}"

    def test_entities_is_list(self):
        parsed = json.loads(export_json(_result()))
        assert isinstance(parsed["entities"], list)

    def test_relationships_is_list(self):
        parsed = json.loads(export_json(_result()))
        assert isinstance(parsed["relationships"], list)

    def test_findings_is_list(self):
        parsed = json.loads(export_json(_result()))
        assert isinstance(parsed["findings"], list)

    def test_warnings_is_list(self):
        parsed = json.loads(export_json(_result()))
        assert isinstance(parsed["warnings"], list)

    def test_empty_result_serialises(self):
        parsed = json.loads(export_json(_result()))
        assert parsed["entities"] == []
        assert parsed["findings"] == []


class TestJsonMetadata:
    def test_metadata_source_type(self):
        parsed = json.loads(export_json(_result(source_type="mysql")))
        assert parsed["analysis_metadata"]["source_type"] == "mysql"

    def test_metadata_source_name(self):
        parsed = json.loads(export_json(_result(source_name="prod.db")))
        assert parsed["analysis_metadata"]["source_name"] == "prod.db"

    def test_metadata_analysed_at(self):
        parsed = json.loads(export_json(_result()))
        assert "analysed_at" in parsed["analysis_metadata"]

    def test_metadata_entity_count(self):
        parsed = json.loads(export_json(_result(entities=[_table("t", [])])))
        assert parsed["analysis_metadata"]["entity_count"] == 1

    def test_metadata_finding_count(self):
        parsed = json.loads(export_json(_result(findings=[_finding()])))
        assert parsed["analysis_metadata"]["finding_count"] == 1

    def test_generator_field_present(self):
        parsed = json.loads(export_json(_result()))
        assert "generator" in parsed["analysis_metadata"]

    def test_note_field_present(self):
        parsed = json.loads(export_json(_result()))
        assert "note" in parsed["analysis_metadata"]

    def test_extra_metadata_included(self):
        parsed = json.loads(export_json(_result(metadata={"version": "1.0"})))
        assert parsed["analysis_metadata"].get("version") == "1.0"

    def test_blocked_metadata_key_excluded(self):
        parsed = json.loads(export_json(_result(metadata={"password": "secret"})))
        assert "password" not in parsed["analysis_metadata"]


class TestJsonEntities:
    def test_entity_name(self):
        parsed = json.loads(export_json(_result(entities=[_table("customers", [])])))
        assert parsed["entities"][0]["name"] == "customers"

    def test_entity_type(self):
        parsed = json.loads(export_json(_result(entities=[_table("customers", [])])))
        assert parsed["entities"][0]["entity_type"] == "table"

    def test_fields_list(self):
        parsed = json.loads(export_json(_result(entities=[
            _table("users", [_field("id", primary_key=True)])
        ])))
        assert len(parsed["entities"][0]["fields"]) == 1

    def test_field_name(self):
        parsed = json.loads(export_json(_result(entities=[
            _table("users", [_field("id", "integer", primary_key=True)])
        ])))
        assert parsed["entities"][0]["fields"][0]["name"] == "id"

    def test_field_data_type(self):
        parsed = json.loads(export_json(_result(entities=[
            _table("users", [_field("id", "integer")])
        ])))
        assert parsed["entities"][0]["fields"][0]["data_type"] == "integer"

    def test_field_primary_key(self):
        parsed = json.loads(export_json(_result(entities=[
            _table("users", [_field("id", primary_key=True)])
        ])))
        assert parsed["entities"][0]["fields"][0]["primary_key"] is True

    def test_field_fk_target(self):
        parsed = json.loads(export_json(_result(entities=[
            _table("orders", [_field("customer_id", foreign_key_target="customers.id")])
        ])))
        assert parsed["entities"][0]["fields"][0]["foreign_key_target"] == "customers.id"

    def test_indexes_included(self):
        parsed = json.loads(export_json(_result(entities=[
            _table("orders", [_field("id")],
                   indexes=[{"name": "idx_x", "columns": ["id"], "unique": False}])
        ])))
        assert len(parsed["entities"][0]["indexes"]) == 1


class TestJsonRelationships:
    def test_declared_rel_source(self):
        parsed = json.loads(export_json(_result(
            relationships=[_rel("orders", "customer_id", "customers", "id")]
        )))
        assert parsed["relationships"][0]["source_entity"] == "orders"

    def test_declared_rel_flag(self):
        parsed = json.loads(export_json(_result(
            relationships=[_rel("orders", "cid", "customers", "id", declared=True)]
        )))
        assert parsed["relationships"][0]["declared"] is True

    def test_inferred_rel_confidence(self):
        parsed = json.loads(export_json(_result(
            relationships=[_rel("orders", "cid", "customers", "id",
                                declared=False, confidence=0.75)]
        )))
        assert parsed["relationships"][0]["confidence"] == pytest.approx(0.75)

    def test_evidence_list_included(self):
        parsed = json.loads(export_json(_result(
            relationships=[_rel("orders", "cid", "customers", "id",
                                evidence=["name match", "type match"])]
        )))
        assert "name match" in parsed["relationships"][0]["evidence"]


class TestJsonFindings:
    def test_finding_rule_id(self):
        parsed = json.loads(export_json(_result(findings=[_finding("SQL-003")])))
        assert parsed["findings"][0]["rule_id"] == "SQL-003"

    def test_finding_severity(self):
        parsed = json.loads(export_json(_result(findings=[_finding(severity="high")])))
        assert parsed["findings"][0]["severity"] == "high"

    def test_finding_entity(self):
        parsed = json.loads(export_json(_result(findings=[_finding(entity="orders")])))
        assert parsed["findings"][0]["entity"] == "orders"

    def test_finding_review_status(self):
        parsed = json.loads(export_json(_result(findings=[_finding(review_status="accepted")])))
        assert parsed["findings"][0]["review_status"] == "accepted"

    def test_finding_evidence_list(self):
        parsed = json.loads(export_json(_result(findings=[_finding()])))
        assert isinstance(parsed["findings"][0]["evidence"], list)

    def test_finding_suggested_command_present(self):
        parsed = json.loads(export_json(_result(
            findings=[_finding(suggested_command="CREATE INDEX x ON t(col);")]
        )))
        assert "CREATE INDEX" in parsed["findings"][0]["suggested_command"]

    def test_finding_confidence_none_serialised(self):
        parsed = json.loads(export_json(_result(findings=[_finding(confidence=None)])))
        assert parsed["findings"][0]["confidence"] is None


class TestJsonSecurity:
    def test_no_raw_password_in_output(self):
        result = _result(metadata={"password": "ultrasecret"})
        out = export_json(result)
        assert "ultrasecret" not in out

    def test_warnings_included_in_output(self):
        parsed = json.loads(export_json(_result(warnings=["View could not be inspected."])))
        assert "View could not be inspected." in parsed["warnings"]


class TestExportJsonDict:
    def test_returns_dict(self):
        d = export_json_dict(_result())
        assert isinstance(d, dict)

    def test_same_keys_as_json(self):
        d = export_json_dict(_result())
        for key in ("analysis_metadata", "entities", "relationships", "findings", "warnings"):
            assert key in d

    def test_entity_count_matches(self):
        d = export_json_dict(_result(entities=[_table("t1", []), _table("t2", [])]))
        assert len(d["entities"]) == 2
