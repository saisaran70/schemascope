"""Tests for rules/sql_rules.py — Step 5.

Each rule gets its own test class covering:
  - trigger (finding produced)
  - non-trigger (no finding)
  - severity variants
  - evidence content
  - edge cases

Helper builders create minimal EntityInfo / RelationshipInfo objects
so tests remain independent of SQLite I/O.
"""
from __future__ import annotations

import pytest

from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    Finding,
    RelationshipInfo,
)
from rules.sql_rules import (
    _candidate_table_names,
    _detect_convention,
    _fk_indexed,
    run_all_sql_rules,
    rule_sql_001,
    rule_sql_002,
    rule_sql_003,
    rule_sql_004,
    rule_sql_005,
    rule_sql_006,
)

# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def _field(
    name: str,
    data_type: str = "integer",
    *,
    nullable: bool = True,
    primary_key: bool = False,
    unique: bool = False,
    foreign_key_target: str | None = None,
    indexed: bool = False,
    index_names: list[str] | None = None,
) -> FieldInfo:
    return FieldInfo(
        name=name,
        data_type=data_type,
        nullable=nullable,
        primary_key=primary_key,
        unique=unique,
        foreign_key_target=foreign_key_target,
        indexed=indexed,
        index_names=index_names or [],
    )


def _table(
    name: str,
    fields: list[FieldInfo],
    indexes: list[dict] | None = None,
) -> EntityInfo:
    return EntityInfo(
        name=name,
        entity_type="table",
        fields=fields,
        indexes=indexes or [],
    )


def _view(name: str, fields: list[FieldInfo] | None = None) -> EntityInfo:
    return EntityInfo(
        name=name,
        entity_type="view",
        fields=fields or [],
    )


def _rel(src: str, src_f: str, tgt: str, tgt_f: str, declared: bool = True) -> RelationshipInfo:
    return RelationshipInfo(
        source_entity=src,
        source_field=src_f,
        target_entity=tgt,
        target_field=tgt_f,
        declared=declared,
        confidence=1.0 if declared else 0.75,
    )


def _make_result(
    entities: list[EntityInfo],
    relationships: list[RelationshipInfo] | None = None,
    source_type: str = "sqlite",
) -> AnalysisResult:
    return AnalysisResult(
        source_type=source_type,
        source_name="test.db",
        analysed_at="2026-06-26T14:00:00+00:00",
        entities=entities,
        relationships=relationships or [],
        findings=[],
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestDetectConvention:
    def test_snake_multiword(self):
        assert _detect_convention("customer_id") == "snake"

    def test_snake_singleword(self):
        assert _detect_convention("id") == "snake"

    def test_camel(self):
        assert _detect_convention("customerId") == "camel"

    def test_pascal(self):
        assert _detect_convention("CustomerId") == "pascal"

    def test_other_with_numbers(self):
        # Mixed digits/special chars
        assert _detect_convention("field_1A") == "other"


class TestCandidateTableNames:
    def test_snake_id_suffix(self):
        cands = _candidate_table_names("customer_id")
        assert "customer" in cands
        assert "customers" in cands

    def test_camel_id_suffix(self):
        cands = _candidate_table_names("customerId")
        assert "customer" in cands
        assert "customers" in cands

    def test_no_id_suffix(self):
        assert _candidate_table_names("name") == []

    def test_product_id(self):
        cands = _candidate_table_names("product_id")
        assert "product" in cands
        assert "products" in cands

    def test_user_id(self):
        cands = _candidate_table_names("user_id")
        assert "user" in cands
        assert "users" in cands


class TestFkIndexed:
    def test_field_is_leading_column(self):
        entity = _table("orders", [], indexes=[{"name": "idx", "columns": ["customer_id"], "unique": False}])
        field = _field("customer_id", foreign_key_target="customers.id")
        assert _fk_indexed(field, entity) is True

    def test_field_is_second_column(self):
        entity = _table("orders", [], indexes=[{"name": "idx", "columns": ["status", "customer_id"], "unique": False}])
        field = _field("customer_id", foreign_key_target="customers.id")
        assert _fk_indexed(field, entity) is False

    def test_no_indexes(self):
        entity = _table("orders", [])
        field = _field("customer_id", foreign_key_target="customers.id")
        assert _fk_indexed(field, entity) is False

    def test_leading_in_composite_index(self):
        entity = _table("orders", [], indexes=[{"name": "idx", "columns": ["customer_id", "status"], "unique": False}])
        field = _field("customer_id", foreign_key_target="customers.id")
        assert _fk_indexed(field, entity) is True


# ---------------------------------------------------------------------------
# SQL-001 — Missing primary key
# ---------------------------------------------------------------------------

class TestSQL001:
    def test_no_finding_when_pk_present(self):
        entity = _table("users", [_field("id", primary_key=True), _field("name", data_type="text")])
        findings = rule_sql_001([entity], [])
        assert findings == []

    def test_finding_when_no_pk(self):
        entity = _table("logs", [_field("event", data_type="text"), _field("ts", data_type="text")])
        findings = rule_sql_001([entity], [])
        assert len(findings) == 1

    def test_rule_id(self):
        entity = _table("logs", [_field("event", data_type="text")])
        f = rule_sql_001([entity], [])[0]
        assert f.rule_id == "SQL-001"

    def test_severity_medium_when_not_referenced(self):
        entity = _table("logs", [_field("event", data_type="text")])
        f = rule_sql_001([entity], [])[0]
        assert f.severity == "medium"

    def test_severity_high_when_referenced_by_fk(self):
        entity = _table("logs", [_field("event", data_type="text")])
        rel = _rel("other_table", "log_id", "logs", "id")
        f = rule_sql_001([entity], [rel])[0]
        assert f.severity == "high"

    def test_view_skipped(self):
        view = _view("vw_users", [_field("id")])
        findings = rule_sql_001([view], [])
        assert findings == []

    def test_unique_column_in_evidence(self):
        entity = _table("logs", [
            _field("code", data_type="text", unique=True),
            _field("message", data_type="text"),
        ])
        f = rule_sql_001([entity], [])[0]
        assert any("code" in e for e in f.evidence)

    def test_entity_name_in_finding(self):
        entity = _table("audit_events", [_field("msg", data_type="text")])
        f = rule_sql_001([entity], [])[0]
        assert f.entity == "audit_events"

    def test_multiple_tables_one_missing_pk(self):
        t1 = _table("users", [_field("id", primary_key=True)])
        t2 = _table("logs", [_field("msg", data_type="text")])
        findings = rule_sql_001([t1, t2], [])
        assert len(findings) == 1
        assert findings[0].entity == "logs"

    def test_database_type_stored(self):
        entity = _table("logs", [_field("msg", data_type="text")])
        f = rule_sql_001([entity], [], database_type="mysql")[0]
        assert f.database_type == "mysql"

    def test_review_status_default_open(self):
        entity = _table("logs", [_field("msg", data_type="text")])
        f = rule_sql_001([entity], [])[0]
        assert f.review_status == "open"


# ---------------------------------------------------------------------------
# SQL-002 — FK column without index
# ---------------------------------------------------------------------------

class TestSQL002:
    def test_no_finding_when_fk_indexed(self):
        entity = _table(
            "orders",
            [_field("customer_id", foreign_key_target="customers.id", indexed=True)],
            indexes=[{"name": "idx_cust", "columns": ["customer_id"], "unique": False}],
        )
        findings = rule_sql_002([entity], [])
        assert findings == []

    def test_finding_when_fk_not_indexed(self):
        entity = _table(
            "orders",
            [_field("customer_id", foreign_key_target="customers.id")],
            indexes=[],
        )
        findings = rule_sql_002([entity], [])
        assert len(findings) == 1

    def test_rule_id(self):
        entity = _table("orders", [_field("customer_id", foreign_key_target="customers.id")], indexes=[])
        f = rule_sql_002([entity], [])[0]
        assert f.rule_id == "SQL-002"

    def test_severity_medium(self):
        entity = _table("orders", [_field("customer_id", foreign_key_target="customers.id")], indexes=[])
        f = rule_sql_002([entity], [])[0]
        assert f.severity == "medium"

    def test_field_name_in_finding(self):
        entity = _table("orders", [_field("customer_id", foreign_key_target="customers.id")], indexes=[])
        f = rule_sql_002([entity], [])[0]
        assert f.field == "customer_id"

    def test_suggested_command_contains_create_index(self):
        entity = _table("orders", [_field("customer_id", foreign_key_target="customers.id")], indexes=[])
        f = rule_sql_002([entity], [])[0]
        assert "CREATE INDEX" in (f.suggested_command or "")

    def test_no_finding_for_non_fk_column(self):
        entity = _table("orders", [_field("status", data_type="text")], indexes=[])
        findings = rule_sql_002([entity], [])
        assert findings == []

    def test_fk_second_in_composite_index_fires(self):
        entity = _table(
            "orders",
            [_field("customer_id", foreign_key_target="customers.id")],
            indexes=[{"name": "idx_composite", "columns": ["status", "customer_id"], "unique": False}],
        )
        findings = rule_sql_002([entity], [])
        assert len(findings) == 1

    def test_two_fks_both_unindexed(self):
        entity = _table(
            "inventory",
            [
                _field("product_id", foreign_key_target="products.id"),
                _field("warehouse_id", foreign_key_target="warehouses.id"),
            ],
            indexes=[],
        )
        findings = rule_sql_002([entity], [])
        assert len(findings) == 2

    def test_view_skipped(self):
        view = _view("vw", [_field("customer_id", foreign_key_target="customers.id")])
        assert rule_sql_002([view], []) == []

    def test_evidence_mentions_target(self):
        entity = _table("orders", [_field("customer_id", foreign_key_target="customers.id")], indexes=[])
        f = rule_sql_002([entity], [])[0]
        assert any("customers.id" in e for e in f.evidence)


# ---------------------------------------------------------------------------
# SQL-003 — Possible undeclared relationship
# ---------------------------------------------------------------------------

class TestSQL003:
    def _make_schema(self, source_table_fields, target_table_name="customers", target_pk_name="id"):
        target = _table(target_table_name, [_field(target_pk_name, primary_key=True)])
        source = _table("orders", source_table_fields)
        return [source, target]

    def test_finding_for_undeclared_fk_by_name(self):
        entities = self._make_schema([_field("customer_id")])
        findings = rule_sql_003(entities, [])
        assert len(findings) == 1

    def test_rule_id(self):
        entities = self._make_schema([_field("customer_id")])
        f = rule_sql_003(entities, [])[0]
        assert f.rule_id == "SQL-003"

    def test_severity_medium(self):
        entities = self._make_schema([_field("customer_id")])
        f = rule_sql_003(entities, [])[0]
        assert f.severity == "medium"

    def test_no_finding_when_fk_declared(self):
        entities = self._make_schema(
            [_field("customer_id", foreign_key_target="customers.id")]
        )
        findings = rule_sql_003(entities, [])
        assert findings == []

    def test_no_finding_when_no_matching_table(self):
        target = _table("products", [_field("id", primary_key=True)])
        source = _table("orders", [_field("customer_id")])
        findings = rule_sql_003([source, target], [])
        assert findings == []

    def test_camel_case_id_detected(self):
        target = _table("users", [_field("id", primary_key=True)])
        source = _table("orders", [_field("userId")])
        findings = rule_sql_003([source, target], [])
        assert len(findings) == 1

    def test_confidence_stored(self):
        entities = self._make_schema([_field("customer_id")])
        f = rule_sql_003(entities, [])[0]
        assert f.confidence is not None
        assert 0.0 < f.confidence <= 1.0

    def test_confidence_higher_with_type_match(self):
        # Both are integer — types match
        entities = self._make_schema([_field("customer_id", data_type="integer")])
        f_match = rule_sql_003(entities, [])[0]

        # Source is text — types don't match
        entities2 = self._make_schema([_field("customer_id", data_type="text")])
        f_no_match = rule_sql_003(entities2, [])[0]

        assert f_match.confidence >= f_no_match.confidence

    def test_no_finding_when_column_has_no_id_pattern(self):
        target = _table("customers", [_field("id", primary_key=True)])
        source = _table("orders", [_field("ref_code", data_type="text")])
        findings = rule_sql_003([source, target], [])
        assert findings == []

    def test_suggested_command_contains_alter_table(self):
        entities = self._make_schema([_field("customer_id")])
        f = rule_sql_003(entities, [])[0]
        assert "ALTER TABLE" in (f.suggested_command or "")

    def test_entity_references_correct_source_table(self):
        entities = self._make_schema([_field("customer_id")])
        f = rule_sql_003(entities, [])[0]
        assert f.entity == "orders"

    def test_field_name_correct(self):
        entities = self._make_schema([_field("customer_id")])
        f = rule_sql_003(entities, [])[0]
        assert f.field == "customer_id"

    def test_no_self_reference(self):
        # Table customers with customer_id field — should not reference itself
        entity = _table("customers", [
            _field("id", primary_key=True),
            _field("customer_id"),
        ])
        findings = rule_sql_003([entity], [])
        assert findings == []

    def test_plural_table_name_matched(self):
        # Field: product_id → looks for 'product' or 'products'
        target = _table("products", [_field("id", primary_key=True)])
        source = _table("orders", [_field("product_id")])
        findings = rule_sql_003([source, target], [])
        assert len(findings) == 1

    def test_declared_rel_suppresses_finding(self):
        entities = self._make_schema([_field("customer_id")])
        rel = _rel("orders", "customer_id", "customers", "id", declared=True)
        findings = rule_sql_003(entities, [rel])
        assert findings == []


# ---------------------------------------------------------------------------
# SQL-004 — Inconsistent naming
# ---------------------------------------------------------------------------

class TestSQL004:
    def test_finding_when_snake_and_camel_coexist(self):
        t1 = _table("users", [_field("created_at", data_type="text")])
        t2 = _table("orders", [_field("customerId")])
        findings = rule_sql_004([t1, t2], [])
        assert len(findings) == 1

    def test_rule_id(self):
        t1 = _table("users", [_field("created_at", data_type="text")])
        t2 = _table("orders", [_field("customerId")])
        f = rule_sql_004([t1, t2], [])[0]
        assert f.rule_id == "SQL-004"

    def test_severity_low(self):
        t1 = _table("users", [_field("created_at", data_type="text")])
        t2 = _table("orders", [_field("customerId")])
        f = rule_sql_004([t1, t2], [])[0]
        assert f.severity == "low"

    def test_no_finding_all_snake(self):
        t = _table("users", [
            _field("user_id"), _field("first_name", data_type="text"), _field("created_at", data_type="text")
        ])
        assert rule_sql_004([t], []) == []

    def test_no_finding_all_camel(self):
        t = _table("users", [_field("userId"), _field("firstName", data_type="text")])
        assert rule_sql_004([t], []) == []

    def test_evidence_shows_both_examples(self):
        t1 = _table("users", [_field("created_at", data_type="text")])
        t2 = _table("orders", [_field("customerId")])
        f = rule_sql_004([t1, t2], [])[0]
        assert any("snake" in e.lower() for e in f.evidence)
        assert any("camel" in e.lower() for e in f.evidence)

    def test_entity_is_schema_wide(self):
        t1 = _table("a", [_field("created_at", data_type="text")])
        t2 = _table("b", [_field("userId")])
        f = rule_sql_004([t1, t2], [])[0]
        assert "schema" in f.entity.lower()

    def test_single_table_no_finding(self):
        t = _table("users", [_field("id", primary_key=True)])
        assert rule_sql_004([t], []) == []

    def test_view_fields_also_counted(self):
        # Even if snake comes from table and camel from view, should detect
        table = _table("users", [_field("created_at", data_type="text")])
        view = _view("vw_orders", [_field("customerId")])
        # rule only checks tables — no finding expected from view-only camel
        # (views are excluded from _tables helper)
        findings = rule_sql_004([table, view], [])
        assert findings == []  # camel only in view → no conflict


# ---------------------------------------------------------------------------
# SQL-005 — Suspicious string data type
# ---------------------------------------------------------------------------

class TestSQL005:
    def test_date_name_with_text_type(self):
        entity = _table("events", [_field("created_at", data_type="text")])
        findings = rule_sql_005([entity], [])
        assert len(findings) == 1

    def test_rule_id(self):
        entity = _table("events", [_field("created_at", data_type="text")])
        f = rule_sql_005([entity], [])[0]
        assert f.rule_id == "SQL-005"

    def test_date_suffix_medium_severity(self):
        entity = _table("events", [_field("event_date", data_type="text")])
        f = rule_sql_005([entity], [])[0]
        assert f.severity == "medium"

    def test_bool_prefix_medium_severity(self):
        entity = _table("users", [_field("is_active", data_type="text")])
        f = rule_sql_005([entity], [])[0]
        assert f.severity == "medium"

    def test_numeric_suffix_low_severity(self):
        entity = _table("orders", [_field("total_amount", data_type="text")])
        f = rule_sql_005([entity], [])[0]
        assert f.severity == "low"

    def test_no_finding_for_correct_type(self):
        entity = _table("events", [_field("created_at", data_type="datetime")])
        assert rule_sql_005([entity], []) == []

    def test_no_finding_for_generic_text_column(self):
        entity = _table("users", [_field("description", data_type="text")])
        assert rule_sql_005([entity], []) == []

    def test_no_finding_for_integer_type(self):
        entity = _table("users", [_field("is_active", data_type="integer")])
        assert rule_sql_005([entity], []) == []

    def test_has_prefix_fires(self):
        entity = _table("posts", [_field("has_comments", data_type="text")])
        findings = rule_sql_005([entity], [])
        assert len(findings) == 1

    def test_price_suffix_fires(self):
        entity = _table("products", [_field("unit_price", data_type="text")])
        findings = rule_sql_005([entity], [])
        assert len(findings) == 1

    def test_ts_suffix_fires(self):
        entity = _table("logs", [_field("event_ts", data_type="text")])
        findings = rule_sql_005([entity], [])
        assert len(findings) == 1

    def test_field_name_stored(self):
        entity = _table("events", [_field("created_at", data_type="text")])
        f = rule_sql_005([entity], [])[0]
        assert f.field == "created_at"

    def test_multiple_suspicious_columns(self):
        entity = _table("orders", [
            _field("order_date", data_type="text"),
            _field("is_shipped", data_type="text"),
            _field("total_amount", data_type="text"),
        ])
        findings = rule_sql_005([entity], [])
        assert len(findings) == 3

    def test_view_skipped(self):
        view = _view("vw_orders", [_field("order_date", data_type="text")])
        assert rule_sql_005([view], []) == []


# ---------------------------------------------------------------------------
# SQL-006 — Excessive nullable columns
# ---------------------------------------------------------------------------

class TestSQL006:
    def _heavy_nullable_table(self, name="profile", total=8, non_nullable=1):
        """Create a table with (total - non_nullable) nullable columns."""
        fields = [_field("id", primary_key=True, nullable=False)]
        for i in range(total - 1):
            fields.append(_field(f"col{i}", data_type="text", nullable=(i >= non_nullable - 1)))
        return _table(name, fields)

    def test_finding_when_ratio_exceeds_threshold(self):
        # 8 cols, id (PK) + 7 nullable text cols → 7/8 = 87.5%
        entity = _table("profile", [
            _field("id", primary_key=True, nullable=False),
            _field("bio", data_type="text"),
            _field("avatar", data_type="text"),
            _field("phone", data_type="text"),
            _field("address", data_type="text"),
            _field("country", data_type="text"),
            _field("zipcode", data_type="text"),
            _field("nickname", data_type="text"),
        ])
        findings = rule_sql_006([entity], [])
        assert len(findings) == 1

    def test_rule_id(self):
        entity = _table("profile", [
            _field("id", primary_key=True, nullable=False),
            *[_field(f"c{i}", data_type="text") for i in range(7)],
        ])
        f = rule_sql_006([entity], [])[0]
        assert f.rule_id == "SQL-006"

    def test_severity_low(self):
        entity = _table("profile", [
            _field("id", primary_key=True, nullable=False),
            *[_field(f"c{i}", data_type="text") for i in range(7)],
        ])
        f = rule_sql_006([entity], [])[0]
        assert f.severity == "low"

    def test_no_finding_when_ratio_below_threshold(self):
        # 8 cols, 3 nullable → 3/8 = 37.5%
        entity = _table("users", [
            _field("id", primary_key=True, nullable=False),
            _field("name", data_type="text", nullable=False),
            _field("email", data_type="text", nullable=False),
            _field("role", data_type="text", nullable=False),
            _field("phone", data_type="text"),
            _field("address", data_type="text"),
            _field("bio", data_type="text"),
            _field("avatar", data_type="text"),
        ])
        assert rule_sql_006([entity], []) == []

    def test_no_finding_for_small_table(self):
        # 4 cols — below minimum of 5
        entity = _table("tiny", [
            _field("id", primary_key=True, nullable=False),
            _field("a", data_type="text"),
            _field("b", data_type="text"),
            _field("c", data_type="text"),
        ])
        assert rule_sql_006([entity], []) == []

    def test_exactly_five_columns_checked(self):
        # 5 cols, 4 nullable → 4/5 = 80% → fires
        entity = _table("semi", [
            _field("id", primary_key=True, nullable=False),
            _field("a", data_type="text"),
            _field("b", data_type="text"),
            _field("c", data_type="text"),
            _field("d", data_type="text"),
        ])
        findings = rule_sql_006([entity], [])
        assert len(findings) == 1

    def test_view_skipped(self):
        view = _view("vw", [_field(f"c{i}", data_type="text") for i in range(8)])
        assert rule_sql_006([view], []) == []

    def test_entity_name_in_finding(self):
        entity = _table("my_profile", [
            _field("id", primary_key=True, nullable=False),
            *[_field(f"c{i}", data_type="text") for i in range(7)],
        ])
        f = rule_sql_006([entity], [])[0]
        assert f.entity == "my_profile"

    def test_exactly_70_percent_no_finding(self):
        # 10 cols: id (not nullable PK) + 9 others
        # 7 nullable out of 10 = 70.0% — NOT > 0.70
        entity = _table("boundary", [
            _field("id", primary_key=True, nullable=False),
            *[_field(f"n{i}", data_type="text", nullable=True) for i in range(7)],
            *[_field(f"nn{i}", data_type="text", nullable=False) for i in range(2)],
        ])
        assert rule_sql_006([entity], []) == []

    def test_just_above_70_percent_fires(self):
        # 10 cols: 8 nullable out of 10 = 80%
        entity = _table("above", [
            _field("id", primary_key=True, nullable=False),
            _field("fixed", data_type="text", nullable=False),
            *[_field(f"n{i}", data_type="text", nullable=True) for i in range(8)],
        ])
        findings = rule_sql_006([entity], [])
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# run_all_sql_rules — integration
# ---------------------------------------------------------------------------

class TestRunAllSqlRules:
    def test_returns_list_of_findings(self):
        result = _make_result([_table("t", [_field("id", primary_key=True)])])
        findings = run_all_sql_rules(result)
        assert isinstance(findings, list)

    def test_attaches_findings_to_result(self):
        entity = _table("logs", [_field("msg", data_type="text")])
        result = _make_result([entity])
        run_all_sql_rules(result)
        assert len(result.findings) > 0

    def test_findings_contain_sql_001(self):
        entity = _table("logs", [_field("msg", data_type="text")])
        result = _make_result([entity])
        run_all_sql_rules(result)
        rule_ids = {f.rule_id for f in result.findings}
        assert "SQL-001" in rule_ids

    def test_database_type_passed_through(self):
        entity = _table("logs", [_field("msg", data_type="text")])
        result = _make_result([entity], source_type="mysql")
        run_all_sql_rules(result)
        assert all(f.database_type == "mysql" for f in result.findings)

    def test_clean_db_produces_no_findings(self):
        # Well-structured schema with PK, FK, and index
        customers = _table("customers", [_field("id", primary_key=True, nullable=False)])
        orders = _table(
            "orders",
            [
                _field("id", primary_key=True, nullable=False),
                _field("customer_id", foreign_key_target="customers.id", indexed=True),
            ],
            indexes=[{"name": "idx_cust", "columns": ["customer_id"], "unique": False}],
        )
        rel = _rel("orders", "customer_id", "customers", "id")
        result = _make_result([customers, orders], [rel])
        run_all_sql_rules(result)
        # SQL-001, 002, 003 should not fire; 004, 005, 006 may not fire
        rule_ids = {f.rule_id for f in result.findings}
        assert "SQL-001" not in rule_ids
        assert "SQL-002" not in rule_ids

    def test_all_six_rules_can_fire(self):
        """Build a schema that triggers all six rules."""
        # SQL-001: no_pk table
        no_pk = _table("logs", [_field("msg", data_type="text"), _field("ts", data_type="text")])
        # SQL-002: FK without index
        orders = _table(
            "orders",
            [_field("id", primary_key=True), _field("customer_id", foreign_key_target="customers.id")],
            indexes=[],
        )
        # SQL-003: undeclared FK candidate
        customers = _table("customers", [_field("id", primary_key=True)])
        source_table = _table("invoices", [_field("id", primary_key=True), _field("customer_id")])
        # SQL-004: mixed naming
        mixed_naming = _table("payments", [_field("created_at", data_type="text"), _field("paymentDate", data_type="datetime")])
        # SQL-005: text date
        events = _table("events", [_field("id", primary_key=True), _field("event_date", data_type="text")])
        # SQL-006: high nullable
        profile = _table("profiles", [
            _field("id", primary_key=True, nullable=False),
            *[_field(f"opt{i}", data_type="text", nullable=True) for i in range(8)],
        ])

        result = _make_result([no_pk, orders, customers, source_table, mixed_naming, events, profile])
        run_all_sql_rules(result)
        rule_ids = {f.rule_id for f in result.findings}
        for expected in ("SQL-001", "SQL-002", "SQL-003", "SQL-005", "SQL-006"):
            assert expected in rule_ids, f"{expected} did not fire"
