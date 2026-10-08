"""infra/template.yaml must define exactly the tables, keys and GSIs in repo/schema.py."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from clearsky.config import REPO_ROOT
from clearsky.repo.schema import TABLES

TEMPLATE = REPO_ROOT / "infra" / "template.yaml"


class _CfnLoader(yaml.SafeLoader):
    pass


def _tag(loader: yaml.SafeLoader, suffix: str, node: yaml.Node) -> Any:
    if isinstance(node, yaml.ScalarNode):
        return {suffix: loader.construct_scalar(node)}
    if isinstance(node, yaml.SequenceNode):
        return {suffix: loader.construct_sequence(node)}
    return {suffix: loader.construct_mapping(node)}  # type: ignore[arg-type]


_CfnLoader.add_multi_constructor("!", _tag)


def _load(path: Path) -> dict[str, Any]:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_CfnLoader)


def _keys(schema: list[dict[str, str]]) -> tuple[str, str | None]:
    h = next(k["AttributeName"] for k in schema if k["KeyType"] == "HASH")
    r = next((k["AttributeName"] for k in schema if k["KeyType"] == "RANGE"), None)
    return h, r


def test_template_tables_match_schema() -> None:
    resources = _load(TEMPLATE)["Resources"]
    tables = {
        r["Properties"]["TableName"]["Sub"].split("-", 1)[1]: r["Properties"]
        for r in resources.values()
        if r["Type"] == "AWS::DynamoDB::Table"
    }
    assert set(tables) == {t.name for t in TABLES}
    for t in TABLES:
        props = tables[t.name]
        assert props["BillingMode"] == "PAY_PER_REQUEST"
        assert _keys(props["KeySchema"]) == (t.hash_key, t.range_key), t.name
        attrs = {a["AttributeName"]: a["AttributeType"] for a in props["AttributeDefinitions"]}
        assert attrs == {a: t.attr_types.get(a, "S") for a in t.key_attributes()}, t.name
        gsis = {g["IndexName"]: _keys(g["KeySchema"]) for g in props.get("GlobalSecondaryIndexes", [])}
        assert gsis == {g.name: (g.hash_key, g.range_key) for g in t.gsis}, t.name
        ttl = props.get("TimeToLiveSpecification", {}).get("AttributeName")
        assert ttl == t.ttl_attribute, t.name


def test_template_handlers_exist() -> None:
    import importlib

    resources = _load(TEMPLATE)["Resources"]
    for name, r in resources.items():
        if r["Type"] != "AWS::Serverless::Function":
            continue
        module, func = r["Properties"]["Handler"].rsplit(".", 1)
        assert callable(getattr(importlib.import_module(module), func)), name
