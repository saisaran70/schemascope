"""Tests for visualizers/mermaid_generator.py — Step 6."""
from __future__ import annotations

import pytest

from models.schema_models import (
    AnalysisResult,
    EntityInfo,
    FieldInfo,
    RelationshipInfo,
)
from visualizers.mermaid_generator import (
    _build_safe_name_map,
    _escape,
    _format_field,
    diagram_warnings,
    generate_er_diagram,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _field(
    name: str,
    data_type: str = "integer",
    primary_key: bool = False,
    foreign_key_target: str | None = None,
    nullable: bool = True,
) -> FieldInfo:
    return FieldInfo(
        name=name,
        data_type=data_type,
        primary_key=primary_key,
        foreign_key_target=foreign_key_target,
        nullable=nullable,
    )


def _table(name: str, fields: list[FieldInfo]) -> EntityInfo:
    return EntityInfo(name=name, entity_type="table", fields=fields)


def _view(name: str, fields: list[FieldInfo] | None = None) -> EntityInfo:
    return EntityInfo(name=name, entity_type="view", fields=fields or [])


def _rel(src: str, src_f: str, tgt: str, tgt_f: str,
         declared: bool = True, confidence: float = 1.0) -> RelationshipInfo:
    return RelationshipInfo(
        source_entity=src, source_field=src_f,
        target_entity=tgt, target_field=tgt_f,
        declared=declared, confidence=confidence,
    )


def _result(
    entities: list[EntityInfo],
    relationships: list[RelationshipInfo] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        source_type="sqlite",
        source_name="test.db",
        analysed_at="2026-06-26T14:00:00+00:00",
        entities=entities,
        relationships=relationships or [],
        findings=[],
        warnings=[],
    )


# ---------------------------------------------------------------------------
# _escape
# ---------------------------------------------------------------------------

class TestEscape:
    def test_plain_name_unchanged(self):
        assert _escape("customers") == "customers"

    def test_spaces_replaced(self):
        assert _escape("my table") == "my_table"

    def test_hyphens_replaced(self):
        assert _escape("order-items") == "order_items"

    def test_dots_replaced(self):
        assert _escape("schema.table") == "schema_table"

    def test_already_safe(self):
        assert _escape("order_items") == "order_items"

    def test_uppercase_preserved(self):
        assert _escape("OrderItems") == "OrderItems"

    def test_numbers_preserved(self):
        assert _escape("table_v2") == "table_v2"

    def test_special_chars_replaced(self):
        assert _escape("table (1)") == "table__1_"


# ---------------------------------------------------------------------------
# _build_safe_name_map
# ---------------------------------------------------------------------------

class TestBuildSafeNameMap:
    def test_unique_names_unchanged(self):
        entities = [_table("customers", []), _table("orders", [])]
        m = _build_safe_name_map(entities)
        assert m["customers"] == "customers"
        assert m["orders"] == "orders"

    def test_collision_gets_suffix(self):
        # "my-table" and "my_table" both escape to "my_table"
        e1 = _table("my-table", [])
        e2 = _table("my_table", [])
        m = _build_safe_name_map([e1, e2])
        assert m["my-table"] != m["my_table"]

    def test_all_names_mapped(self):
        entities = [_table(f"t{i}", []) for i in range(5)]
        m = _build_safe_name_map(entities)
        assert len(m) == 5


# ---------------------------------------------------------------------------
# _format_field
# ---------------------------------------------------------------------------

class TestFormatField:
    def test_plain_field(self):
        f = _field("name", "text")
        line = _format_field(f)
        assert "text" in line
        assert "name" in line

    def test_pk_marker(self):
        f = _field("id", "integer", primary_key=True)
        assert "PK" in _format_field(f)

    def test_fk_marker(self):
        f = _field("customer_id", "integer", foreign_key_target="customers.id")
        assert "FK" in _format_field(f)

    def test_pk_and_fk_marker(self):
        f = FieldInfo(
            name="id", data_type="integer",
            primary_key=True, foreign_key_target="other.id",
        )
        line = _format_field(f)
        assert "PK" in line
        assert "FK" in line

    def test_no_marker_for_plain_field(self):
        f = _field("status", "text")
        line = _format_field(f)
        assert "PK" not in line
        assert "FK" not in line

    def test_spaces_in_type_replaced(self):
        f = FieldInfo(name="val", data_type="double precision")
        line = _format_field(f)
        assert " " not in line.split()[0]  # type token must be single word

    def test_field_name_escaped(self):
        f = _field("my-field", "text")
        line = _format_field(f)
        assert "my_field" in line


# ---------------------------------------------------------------------------
# generate_er_diagram — structure
# ---------------------------------------------------------------------------

class TestGenerateErDiagramStructure:
    def test_starts_with_erdiagram(self):
        result = _result([_table("users", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result)
        assert out.startswith("erDiagram")

    def test_entity_block_present(self):
        result = _result([_table("users", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result)
        assert "users" in out
        assert "{" in out
        assert "}" in out

    def test_field_in_entity_block(self):
        result = _result([_table("users", [_field("id", "integer", primary_key=True)])])
        out = generate_er_diagram(result)
        assert "id" in out
        assert "integer" in out

    def test_pk_marker_in_output(self):
        result = _result([_table("users", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result)
        assert "PK" in out

    def test_fk_marker_in_output(self):
        result = _result([
            _table("orders", [
                _field("id", primary_key=True),
                _field("customer_id", "integer", foreign_key_target="customers.id"),
            ]),
            _table("customers", [_field("id", primary_key=True)]),
        ])
        out = generate_er_diagram(result)
        assert "FK" in out

    def test_multiple_entity_blocks(self):
        result = _result([
            _table("customers", [_field("id", primary_key=True)]),
            _table("orders", [_field("id", primary_key=True)]),
        ])
        out = generate_er_diagram(result)
        assert "customers" in out
        assert "orders" in out

    def test_empty_result_shows_comment(self):
        result = _result([])
        out = generate_er_diagram(result)
        assert out.startswith("erDiagram")
        assert "%%" in out

    def test_view_entity_included(self):
        result = _result([
            _table("users", [_field("id", primary_key=True)]),
            _view("vw_users", [_field("id"), _field("name", "text")]),
        ])
        out = generate_er_diagram(result)
        assert "vw_users" in out


# ---------------------------------------------------------------------------
# generate_er_diagram — relationships
# ---------------------------------------------------------------------------

class TestGenerateErDiagramRelationships:
    def test_declared_fk_solid_connector(self):
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id", foreign_key_target="customers.id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id", declared=True)],
        )
        out = generate_er_diagram(result)
        assert "||--o{" in out

    def test_inferred_rel_dashed_connector(self):
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id",
                                declared=False, confidence=0.75)],
        )
        out = generate_er_diagram(result)
        assert "||..o{" in out

    def test_inferred_rel_shows_confidence(self):
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id",
                                declared=False, confidence=0.75)],
        )
        out = generate_er_diagram(result)
        assert "75%" in out

    def test_relationship_label_uses_field_name(self):
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id")],
        )
        out = generate_er_diagram(result)
        assert "customer_id" in out

    def test_no_relationship_when_no_fks(self):
        result = _result([_table("standalone", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result)
        assert "||" not in out

    def test_multiple_relationships(self):
        result = _result(
            entities=[
                _table("products", [_field("id", primary_key=True)]),
                _table("warehouses", [_field("id", primary_key=True)]),
                _table("inventory", [
                    _field("product_id", foreign_key_target="products.id"),
                    _field("warehouse_id", foreign_key_target="warehouses.id"),
                ]),
            ],
            relationships=[
                _rel("inventory", "product_id", "products", "id"),
                _rel("inventory", "warehouse_id", "warehouses", "id"),
            ],
        )
        out = generate_er_diagram(result)
        assert out.count("||--o{") == 2

    def test_relationship_excluded_when_target_filtered(self):
        """When target entity is not in selected_entities, hide the relationship."""
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id")],
        )
        # Only include orders, not customers
        out = generate_er_diagram(result, selected_entities=["orders"])
        assert "||--o{" not in out

    def test_both_declared_and_inferred_in_same_diagram(self):
        result = _result(
            entities=[
                _table("a", [_field("id", primary_key=True)]),
                _table("b", [_field("id", primary_key=True)]),
                _table("c", [_field("id", primary_key=True)]),
            ],
            relationships=[
                _rel("b", "a_id", "a", "id", declared=True),
                _rel("c", "b_id", "b", "id", declared=False, confidence=0.80),
            ],
        )
        out = generate_er_diagram(result)
        assert "||--o{" in out
        assert "||..o{" in out


# ---------------------------------------------------------------------------
# generate_er_diagram — entity filtering
# ---------------------------------------------------------------------------

class TestEntityFiltering:
    def test_selected_entities_only_shown(self):
        result = _result([
            _table("customers", [_field("id", primary_key=True)]),
            _table("orders", [_field("id", primary_key=True)]),
            _table("products", [_field("id", primary_key=True)]),
        ])
        out = generate_er_diagram(result, selected_entities=["customers"])
        assert "customers" in out
        assert "orders" not in out
        assert "products" not in out

    def test_unrecognised_selected_entity_ignored(self):
        result = _result([_table("users", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result, selected_entities=["nonexistent"])
        assert "nonexistent" not in out
        assert "%%" in out  # empty → comment

    def test_all_entities_shown_when_no_filter(self):
        result = _result([
            _table("a", [_field("id", primary_key=True)]),
            _table("b", [_field("id", primary_key=True)]),
        ])
        out = generate_er_diagram(result)
        assert "a" in out
        assert "b" in out


# ---------------------------------------------------------------------------
# generate_er_diagram — large schema limit
# ---------------------------------------------------------------------------

class TestLargeSchemaLimit:
    def _big_result(self, count: int) -> AnalysisResult:
        return _result([_table(f"table_{i}", [_field("id", primary_key=True)]) for i in range(count)])

    def test_exactly_50_entities_rendered(self):
        result = self._big_result(50)
        out = generate_er_diagram(result, max_entities=50)
        assert out.startswith("erDiagram")
        assert "%% Schema has" not in out

    def test_51_entities_shows_warning_comment(self):
        result = self._big_result(51)
        out = generate_er_diagram(result, max_entities=50)
        assert "erDiagram" in out
        assert "%%" in out
        assert "51" in out

    def test_over_limit_with_filter_renders_diagram(self):
        result = self._big_result(60)
        selected = [f"table_{i}" for i in range(10)]
        out = generate_er_diagram(result, selected_entities=selected, max_entities=50)
        assert "table_0" in out
        assert "%% Schema has" not in out

    def test_custom_max_entities_respected(self):
        result = self._big_result(10)
        out = generate_er_diagram(result, max_entities=5)
        assert "%%" in out
        assert "10" in out


# ---------------------------------------------------------------------------
# generate_er_diagram — entity name escaping
# ---------------------------------------------------------------------------

class TestEntityNameEscaping:
    def test_hyphenated_name_escaped_in_block(self):
        result = _result([_table("order-items", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result)
        assert "order_items" in out
        assert "order-items" not in out

    def test_spaced_name_escaped(self):
        result = _result([_table("my table", [_field("id", primary_key=True)])])
        out = generate_er_diagram(result)
        assert "my_table" in out

    def test_escaped_name_used_in_relationship(self):
        result = _result(
            entities=[
                _table("order-items", [_field("id", primary_key=True)]),
                _table("products", [_field("id", primary_key=True)]),
            ],
            relationships=[_rel("order-items", "product_id", "products", "id")],
        )
        out = generate_er_diagram(result)
        assert "order_items" in out
        assert "order-items" not in out


# ---------------------------------------------------------------------------
# diagram_warnings
# ---------------------------------------------------------------------------

class TestDiagramWarnings:
    def test_no_warnings_for_small_schema(self):
        result = _result([_table("users", [_field("id", primary_key=True)])])
        assert diagram_warnings(result) == []

    def test_warning_when_over_limit(self):
        entities = [_table(f"t{i}", [_field("id", primary_key=True)]) for i in range(60)]
        result = _result(entities)
        w = diagram_warnings(result, max_entities=50)
        assert len(w) == 1
        assert "60" in w[0]

    def test_hidden_relationship_warning_with_filter(self):
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id")],
        )
        w = diagram_warnings(result, selected_entities=["orders"])
        assert len(w) == 1
        assert "endpoint" in w[0].lower() or "relationship" in w[0].lower()

    def test_no_hidden_rel_warning_when_both_endpoints_selected(self):
        result = _result(
            entities=[
                _table("customers", [_field("id", primary_key=True)]),
                _table("orders", [_field("customer_id")]),
            ],
            relationships=[_rel("orders", "customer_id", "customers", "id")],
        )
        w = diagram_warnings(result, selected_entities=["customers", "orders"])
        assert w == []
