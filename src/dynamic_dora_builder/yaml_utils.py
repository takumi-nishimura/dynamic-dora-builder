from __future__ import annotations

from typing import Any

import yaml


class _IndentedSafeDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, indentless=False)


def dump_yaml(data: Any) -> str:
    return yaml.dump(
        data,
        Dumper=_IndentedSafeDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        indent=2,
    )
