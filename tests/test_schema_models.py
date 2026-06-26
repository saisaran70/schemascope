"""Tests for schema_models dataclasses — Step 1."""
import dataclasses
import json

import pytest

from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    Finding,
    RelationshipInfo,
)


# ---------------------------------------------------------------------------
# FieldInfo
# ---------------------------------------------------------------------------

class TestFieldInfo:
    def test_required_fields_only(self):
        f = FieldInfo(name="id", data_type="integer")
        assert f.name == "id"
        assert f.data_type == "integer"

    def test_defaults(self):
        f = FieldInfo(name="col", data_type="text")
        assert f.nullable is True
        assert f.primary_key is False
        assert f.unique is False
        assert f.default_value is None
        assert f.foreign_key_target is None
        assert f.indexed is False
        assert f.index_names == []
        assert f.occurrence_rate is None
        assert f.metadata == {}

    def test_primary_key_field(self):
        f = FieldInfo(name="id", data_type="integer", primary_key=True, nullable=False)
        assert f.primary_key is True
        assert f.nullable is False

    def test_foreign_key_field(self):
        f = FieldInfo(
            name="customer_id",
            data_type="integer",
            foreign_key_target="customers.id",
            indexed=True,
            index_names=["idx_orders_customer_id"],
        )
        assert f.foreign_key_target == "customers.id"
        assert f.indexed is True
        assert "idx_orders_customer_id" in f.index_names

    def test_occurrence_rate_for_mongodb(self):
        f = FieldInfo(name="userId", data_type="ObjectId", occurrence_rate=0.99)
        assert f.occurrence_rate == pytest.approx(0.99)

    def test_index_names_are_independent_per_instance(self):
        """Mutable default must not be shared between instances."""
        f1 = FieldInfo(name="a", data_type="text")
        f2 = FieldInfo(name="b", data_type="text")
        f1.index_names.append("idx_a")
        assert f2.index_names == []

    def test_metadata_dict_is_independent_per_instance(self):
        f1 = FieldInfo(name="a", data_type="text")
        f2 = FieldInfo(name="b", data_type="text")
        f1.metadata["key"] = "val"
        assert "key" not in f2.metadata


# ---------------------------------------------------------------------------
# EntityInfo
# ---------------------------------------------------------------------------

class TestEntityInfo:
    def _make_field(self, name="id", data_type="integer"):
        return FieldInfo(name=name, data_type=data_type)

    def test_basic_construction(self):
        e = EntityInfo(
            name="orders",
            entity_type="table",
            fields=[self._make_field()],
        )
        assert e.name == "orders"
        assert e.entity_type == "table"
        assert len(e.fields) == 1

    def test_view_entity_type(self):
        e = EntityInfo(name="vw_summary", entity_type="view", fields=[])
        assert e.entity_type == "view"

    def test_collection_entity_type(self):
        e = EntityInfo(name="users", entity_type="collection", fields=[])
        assert e.entity_type == "collection"

    def test_defaults(self):
        e = EntityInfo(name="t", entity_type="table", fields=[])
        assert e.indexes == []
        assert e.row_count is None
        assert e.metadata == {}

    def test_with_indexes(self):
        e = EntityInfo(
            name="orders",
            entity_type="table",
            fields=[],
            indexes=[{"name": "idx_status", "columns": ["status"], "unique": False}],
        )
        assert len(e.indexes) == 1
        assert e.indexes[0]["name"] == "idx_status"

    def test_indexes_list_independent_per_instance(self):
        e1 = EntityInfo(name="t1", entity_type="table", fields=[])
        e2 = EntityInfo(name="t2", entity_type="table", fields=[])
        e1.indexes.append({"name": "idx_x"})
        assert e2.indexes == []

    def test_empty_fields_list_allowed(self):
        e = EntityInfo(name="empty_table", entity_type="table", fields=[])
        assert e.fields == []


# ---------------------------------------------------------------------------
# RelationshipInfo
# ---------------------------------------------------------------------------

class TestRelationshipInfo:
    def test_declared_relationship(self):
        r = RelationshipInfo(
            source_entity="orders",
            source_field="customer_id",
            target_entity="customers",
            target_field="id",
            declared=True,
            confidence=1.0,
            evidence=["foreign key constraint"],
        )
        assert r.declared is True
        assert r.confidence == pytest.approx(1.0)
        assert "foreign key constraint" in r.evidence

    def test_inferred_relationship(self):
        r = RelationshipInfo(
            source_entity="orders",
            source_field="product_id",
            target_entity="products",
            target_field="id",
            declared=False,
            confidence=0.75,
            evidence=["name match", "type match"],
        )
        assert r.declared is False
        assert r.confidence == pytest.approx(0.75)
        assert len(r.evidence) == 2

    def test_defaults(self):
        r = RelationshipInfo(
            source_entity="a",
            source_field="b_id",
            target_entity="b",
            target_field="id",
            declared=True,
            confidence=1.0,
        )
        assert r.evidence == []
        assert r.relationship_type is None

    def test_evidence_list_independent_per_instance(self):
        r1 = RelationshipInfo("a", "b_id", "b", "id", True, 1.0)
        r2 = RelationshipInfo("c", "d_id", "d", "id", True, 1.0)
        r1.evidence.append("reason")
        assert r2.evidence == []

    def test_confidence_zero_for_weak(self):
        r = RelationshipInfo("a", "x", "b", "id", False, 0.0)
        assert r.confidence == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

class TestFinding:
    def _make_finding(self, **kwargs):
        defaults = dict(
            rule_id="SQL-001",
            database_type="sqlite",
            entity="orders",
            severity="medium",
            title="Missing primary key",
            description="Table orders has no declared primary key.",
            evidence=["no PK constraint found"],
            impact="Rows cannot be uniquely identified.",
            recommendation="Add a primary key column.",
        )
        defaults.update(kwargs)
        return Finding(**defaults)

    def test_basic_construction(self):
        f = self._make_finding()
        assert f.rule_id == "SQL-001"
        assert f.severity == "medium"

    def test_default_review_status_is_open(self):
        f = self._make_finding()
        assert f.review_status == "open"

    def test_review_status_accepted(self):
        f = self._make_finding(review_status="accepted")
        assert f.review_status == "accepted"

    def test_review_status_ignored(self):
        f = self._make_finding(review_status="ignored")
        assert f.review_status == "ignored"

    def test_optional_field_defaults_to_none(self):
        f = self._make_finding()
        assert f.field is None
        assert f.confidence is None
        assert f.suggested_command is None

    def test_with_field_and_command(self):
        f = self._make_finding(
            rule_id="SQL-002",
            field="customer_id",
            suggested_command="CREATE INDEX idx ON orders(customer_id);",
        )
        assert f.field == "customer_id"
        assert "CREATE INDEX" in f.suggested_command

    def test_evidence_list_independent_per_instance(self):
        f1 = self._make_finding()
        f2 = self._make_finding()
        f1.evidence.append("extra")
        assert "extra" not in f2.evidence

    def test_all_severity_levels_accepted(self):
        for sev in ("high", "medium", "low", "information"):
            f = self._make_finding(severity=sev)
            assert f.severity == sev

    def test_all_database_types_accepted(self):
        for db in ("sqlite", "mysql", "mongodb"):
            f = self._make_finding(database_type=db)
            assert f.database_type == db


# ---------------------------------------------------------------------------
# AnalysisResult
# ---------------------------------------------------------------------------

class TestAnalysisResult:
    def _make_result(self, **kwargs):
        defaults = dict(
            source_type="sqlite",
            source_name="test.db",
            analysed_at="2026-06-26T14:00:00Z",
            entities=[],
            relationships=[],
            findings=[],
            warnings=[],
        )
        defaults.update(kwargs)
        return AnalysisResult(**defaults)

    def test_basic_construction(self):
        r = self._make_result()
        assert r.source_type == "sqlite"
        assert r.source_name == "test.db"
        assert r.entities == []

    def test_defaults(self):
        r = self._make_result()
        assert r.metadata == {}

    def test_with_entities(self):
        entity = EntityInfo(
            name="users",
            entity_type="table",
            fields=[FieldInfo(name="id", data_type="integer", primary_key=True)],
        )
        r = self._make_result(entities=[entity])
        assert len(r.entities) == 1
        assert r.entities[0].name == "users"

    def test_with_relationships(self):
        rel = RelationshipInfo("orders", "user_id", "users", "id", True, 1.0)
        r = self._make_result(relationships=[rel])
        assert len(r.relationships) == 1
        assert r.relationships[0].source_entity == "orders"

    def test_with_findings(self):
        finding = Finding(
            rule_id="SQL-001",
            database_type="sqlite",
            entity="orders",
            severity="medium",
            title="Missing PK",
            description="No PK.",
            evidence=[],
            impact="Bad.",
            recommendation="Add PK.",
        )
        r = self._make_result(findings=[finding])
        assert len(r.findings) == 1

    def test_with_warnings(self):
        r = self._make_result(warnings=["View vw_x could not be inspected."])
        assert len(r.warnings) == 1

    def test_metadata_dict_independent_per_instance(self):
        r1 = self._make_result()
        r2 = self._make_result()
        r1.metadata["key"] = "value"
        assert "key" not in r2.metadata

    def test_analysed_at_is_string(self):
        r = self._make_result(analysed_at="2026-01-01T00:00:00Z")
        assert isinstance(r.analysed_at, str)


# ---------------------------------------------------------------------------
# Serialization via dataclasses.asdict
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_field_info_asdict(self):
        f = FieldInfo(name="id", data_type="integer", primary_key=True)
        d = dataclasses.asdict(f)
        assert d["name"] == "id"
        assert d["primary_key"] is True

    def test_analysis_result_asdict_is_json_serializable(self):
        entity = EntityInfo(
            name="users",
            entity_type="table",
            fields=[
                FieldInfo(name="id", data_type="integer", primary_key=True),
                FieldInfo(name="name", data_type="text"),
            ],
        )
        rel = RelationshipInfo("orders", "user_id", "users", "id", True, 1.0)
        finding = Finding(
            rule_id="SQL-001",
            database_type="sqlite",
            entity="logs",
            severity="medium",
            title="Missing PK",
            description="No PK on logs.",
            evidence=["no PK constraint"],
            impact="Rows not uniquely identifiable.",
            recommendation="Add PK.",
        )
        result = AnalysisResult(
            source_type="sqlite",
            source_name="test.db",
            analysed_at="2026-06-26T14:00:00Z",
            entities=[entity],
            relationships=[rel],
            findings=[finding],
            warnings=["one warning"],
        )
        d = dataclasses.asdict(result)
        # Must be JSON-serializable (no datetime objects, no unserializable types)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        assert loaded["source_type"] == "sqlite"
        assert loaded["entities"][0]["name"] == "users"
        assert loaded["relationships"][0]["declared"] is True
        assert loaded["findings"][0]["review_status"] == "open"
        assert loaded["warnings"] == ["one warning"]

    def test_nested_field_in_entity_survives_round_trip(self):
        entity = EntityInfo(
            name="orders",
            entity_type="table",
            fields=[
                FieldInfo(
                    name="customer_id",
                    data_type="integer",
                    foreign_key_target="customers.id",
                    indexed=True,
                    index_names=["idx_orders_customer"],
                )
            ],
        )
        d = dataclasses.asdict(entity)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        fld = loaded["fields"][0]
        assert fld["foreign_key_target"] == "customers.id"
        assert fld["index_names"] == ["idx_orders_customer"]
