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
        deployment = DeploymentConfig.model_validate(
            yaml.safe_load(deployment_path.read_text())
        )

        dataflow = Dataflow()
        for node in deployment.nodes:
            if isinstance(node, (Node, Operator)):
                dataflow.nodes.append(node)
            elif isinstance(node, DynamicNode):
                loaded_dataflow = Dataflow.model_validate(
                    yaml.safe_load(Path(node.path).read_text())
                )
                if matched := next(
                    (n for n in loaded_dataflow.nodes if n.id == node.id), None
                ):
                    dataflow.nodes.append(matched)

        for component in deployment.components:
            component_path = Path(component.path)
            template_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(component_path.parent))
            )
            template = template_env.get_template(component_path.name)
            rendered_dataflow = template.render(component.env or {})
            replaced_dataflow = yaml.safe_load(rendered_dataflow)

            loaded_dataflow = Dataflow.model_validate(replaced_dataflow)
            for node in loaded_dataflow.nodes:
                dataflow.nodes.append(node)

        if export_path:
            if not export_path.parent.exists():
                export_path.parent.mkdir(parents=True, exist_ok=True)
            export_path.write_text(
                dump_yaml(dataflow.model_dump(exclude_none=True))
            )

        return dataflow
