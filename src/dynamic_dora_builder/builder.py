import os
from pathlib import Path
from typing import Optional

import jinja2
import yaml

from .models import Dataflow, DeploymentConfig, DynamicNode, Node, Operator
from .yaml_utils import dump_yaml


class DynamicDataflowBuilder:
    @classmethod
    def build(
        cls, deployment_path: Path, export_path: Optional[Path] = None
    ) -> Dataflow:
        command_root = Path.cwd().resolve()
        deployment_path = deployment_path.resolve()

        dataflow = cls._build_dataflow(deployment_path, command_root)
        cls._relativize_dataflow_paths(dataflow, command_root)

        if export_path:
            normalized_export_path = cls._prepare_export_path(export_path, command_root)
            normalized_export_path.write_text(
                dump_yaml(dataflow.model_dump(exclude_none=True))
            )

        return dataflow

    @classmethod
    def _build_dataflow(cls, deployment_path: Path, command_root: Path) -> Dataflow:
        rendered_deployment = cls._render_deployment_template(
            deployment_path, command_root
        )
        deployment = DeploymentConfig.model_validate(
            yaml.safe_load(rendered_deployment) or {}
        )
        deployment_dir = deployment_path.parent

        dataflow = Dataflow()
        for node in deployment.nodes:
            if isinstance(node, Node):
                dataflow.nodes.append(
                    cls._normalize_node(node, deployment_dir, command_root)
                )
            elif isinstance(node, Operator):
                dataflow.nodes.append(
                    cls._normalize_operator(node, deployment_dir, command_root)
                )
            elif isinstance(node, DynamicNode):
                resolved_dynamic_path = cls._resolve_path_for_io(
                    node.path, deployment_dir, command_root
                )
                loaded_dataflow = cls._load_dataflow_from_path(
                    resolved_dynamic_path, command_root
                )
                matched = next(
                    (
                        n
                        for n in loaded_dataflow.nodes
                        if isinstance(n, Node) and n.id == node.id
                    ),
                    None,
                )
                if matched:
                    dataflow.nodes.append(matched)

        for component in deployment.components:
            component_path = cls._resolve_path_for_io(
                component.path, deployment_dir, command_root
            )
            template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(component_path.parent))
            )
            template = template_env.get_template(component_path.name)
            rendered_dataflow = template.render(component.env or {})
            replaced_dataflow = yaml.safe_load(rendered_dataflow) or {}

            loaded_dataflow = Dataflow.model_validate(replaced_dataflow)
            normalized = cls._normalize_dataflow(
                loaded_dataflow, component_path.parent, command_root
            )
            for node in normalized.nodes:
                dataflow.nodes.append(node)

        return dataflow

    @staticmethod
    def _render_deployment_template(deployment_path: Path, command_root: Path) -> str:
        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(deployment_path.parent)),
            undefined=jinja2.StrictUndefined,
        )
        template = template_env.get_template(deployment_path.name)
        context = {"env": os.environ, "cwd": str(command_root)}
        return template.render(context)

    @staticmethod
    def _resolve_path_for_io(raw_path: str, base_dir: Path, command_root: Path) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            base_candidate = (base_dir / path).resolve()
            if base_candidate.exists():
                return base_candidate
            fallback_candidate = (command_root / path).resolve()
            if fallback_candidate.exists():
                return fallback_candidate
            return base_candidate
        return path.resolve()

    @classmethod
    def _normalize_node(cls, node: Node, base_dir: Path, command_root: Path) -> Node:
        node_copy = node.model_copy(deep=True)
        if node_copy.path:
            node_copy.path = str(
                cls._resolve_path_value(node_copy.path, base_dir, command_root)
            )
        if node_copy.operator:
            node_copy.operator = cls._normalize_operator(
                node_copy.operator, base_dir, command_root
            )
        return node_copy

    @classmethod
    def _normalize_operator(
        cls, operator: Operator, base_dir: Path, command_root: Path
    ) -> Operator:
        operator_copy = operator.model_copy(deep=True)
        if operator_copy.python:
            operator_copy.python = str(
                cls._resolve_path_value(operator_copy.python, base_dir, command_root)
            )
        return operator_copy

    @staticmethod
    def _resolve_path_value(raw_path: str, base_dir: Path, command_root: Path) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path.resolve()
        base_candidate = (base_dir / path).resolve()
        if base_candidate.exists():
            return base_candidate
        fallback_candidate = (command_root / path).resolve()
        if fallback_candidate.exists():
            return fallback_candidate
        return base_candidate

    @classmethod
    def _normalize_dataflow(
        cls, dataflow: Dataflow, base_dir: Path, command_root: Path
    ) -> Dataflow:
        normalized = Dataflow()
        for node in dataflow.nodes:
            if isinstance(node, Node):
                normalized.nodes.append(
                    cls._normalize_node(node, base_dir, command_root)
                )
            elif isinstance(node, Operator):
                normalized.nodes.append(
                    cls._normalize_operator(node, base_dir, command_root)
                )
        return normalized

    @classmethod
    def _load_dataflow_from_path(cls, path: Path, command_root: Path) -> Dataflow:
        rendered = yaml.safe_load(path.read_text()) or {}
        dataflow = Dataflow.model_validate(rendered)
        return cls._normalize_dataflow(dataflow, path.parent, command_root)

    @staticmethod
    def _relativize_path(value: str, root: Path) -> str:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return os.path.relpath(candidate, root)

    @classmethod
    def _relativize_operator_paths(cls, operator: Operator, root: Path) -> None:
        if operator.python:
            operator.python = cls._relativize_path(operator.python, root)

    @classmethod
    def _relativize_node_paths(cls, node: Node, root: Path) -> None:
        if node.path:
            node.path = cls._relativize_path(node.path, root)
        if node.operator:
            cls._relativize_operator_paths(node.operator, root)

    @classmethod
    def _relativize_dataflow_paths(cls, dataflow: Dataflow, root: Path) -> None:
        for node in dataflow.nodes:
            if isinstance(node, Node):
                cls._relativize_node_paths(node, root)
            elif isinstance(node, Operator):
                cls._relativize_operator_paths(node, root)

    @staticmethod
    def _prepare_export_path(export_path: Path, command_root: Path) -> Path:
        if not export_path.is_absolute():
            export_path = command_root / export_path
        export_path = export_path.resolve()
        if not export_path.parent.exists():
            export_path.parent.mkdir(parents=True, exist_ok=True)
        return export_path
