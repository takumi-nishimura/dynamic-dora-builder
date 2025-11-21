from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class Dataflow(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True, union_mode="left_to_right"
    )

    nodes: List[Union["Node", "Operator"]] = Field(
        default=[], description="List of nodes and operators in the dataflow"
    )


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the node")
    path: Optional[str] = Field(
        default=None, description="Path to the executable or script"
    )
    env: Optional[Dict[str, Any]] = Field(
        default=None, description="Environment variables for the node"
    )
    name: Optional[str] = Field(
        default=None, description="Human-readable name for the node"
    )
    build: Optional[str] = Field(default=None, description="Build command for the node")
    operator: Optional["Operator"] = Field(
        default=None, description="Operator associated with the node"
    )
    inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Input dependencies for the node"
    )
    outputs: Optional[List[str]] = Field(
        default=None, description="Output artifacts for the node"
    )
    args: Optional[Union[List[str], str]] = Field(
        default=None,
        description="Command-line arguments passed to the node executable (list or string)",
    )

    @property
    def config(self) -> Dict[str, str]:
        return self.model_dump()


class Operator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    build: Optional[str] = Field(
        default=None, description="Build command for the operator"
    )
    description: Optional[str] = Field(
        default=None, description="Description of the operator"
    )
    python: Optional[str] = Field(
        default=None, description="Python script path for the operator"
    )
    inputs: Optional[Dict[str, Any]] = Field(
        default=None, description="Input dependencies for the operator"
    )
    env: Optional[Dict[str, Any]] = Field(
        default=None, description="Environment variables for the operator"
    )
    outputs: Optional[List[str]] = Field(
        default=None, description="Output artifacts for the operator"
    )
    args: Optional[Union[List[str], str]] = Field(
        default=None,
        description="Command-line arguments passed to the operator executable (list or string)",
    )


class DeploymentConfig(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True, union_mode="left_to_right"
    )

    vars: Optional[Dict[str, Any]] = Field(
        default=None, description="Jinja template variables available as plain keys or under vars"
    )
    nodes: List[Union[Node, Operator, "DynamicNode"]] = Field(
        default=[],
        description="List of nodes, operators, and dynamic nodes in the deployment",
    )
    components: List["DynamicComponent"] = Field(
        default=[], description="List of dynamic components in the deployment"
    )


class DynamicNode(BaseModel):
    id: str = Field(..., description="Unique identifier for the dynamic node")
    path: str = Field(..., description="Path to the executable or script")
    kind: Literal["dynamic"] = Field(
        default="dynamic", description="Kind of the node, fixed to 'dynamic'"
    )


class DynamicComponent(BaseModel):
    id: str = Field(..., description="Unique identifier for the dynamic component")
    path: str = Field(..., description="Path to the component's definition")
    vars: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Template variables used for rendering this component.",
    )
