from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .builder import DynamicDataflowBuilder
from .models import Dataflow
from .yaml_utils import dump_yaml


def _dump_dataflow_to_stdout(dataflow: Dataflow) -> None:
    rendered = dump_yaml(dataflow.model_dump(exclude_none=True))
    sys.stdout.write(rendered)


def build_command(
    deployment: Path,
    export: Path | None,
    emit_stdout: bool,
    notify_export: bool,
) -> int:
    dataflow = DynamicDataflowBuilder.build(
        deployment_path=deployment, export_path=export
    )

    if emit_stdout:
        _dump_dataflow_to_stdout(dataflow)

    if export:
        if notify_export:
            print(f"Dataflow exported to {export}", file=sys.stderr)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dynamic-dora-builder")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="Build a dataflow from a deployment configuration",
    )
    build_parser.add_argument(
        "deployment",
        type=Path,
        help="Path to the deployment YAML file",
    )
    build_parser.add_argument(
        "--export",
        type=Path,
        help="Optional path to export the rendered dataflow YAML",
    )
    build_parser.add_argument(
        "--stdout",
        action="store_true",
        help="Always print the rendered dataflow to stdout",
    )

    args = parser.parse_args(argv)

    if args.command == "build":
        if not args.deployment.exists():
            parser.error(f"Deployment file not found: {args.deployment}")
        if args.export and args.export.is_dir():
            parser.error("--export must point to a file, not a directory")

        export_path = args.export or Path("dataflow.yml")
        implicit_export = args.export is None
        return build_command(
            deployment=args.deployment,
            export=export_path,
            emit_stdout=args.stdout or implicit_export,
            notify_export=True,
        )

    parser.error("Unknown command")
    return 2


def console_main(argv: Sequence[str] | None = None) -> None:
    raise SystemExit(main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
