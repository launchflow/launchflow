import dataclasses
from enum import Enum
from functools import wraps
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar, get_args

from launchflow import exceptions
from launchflow.models.enums import CloudProvider


def _serialize_type(val: Any) -> Any:
    if isinstance(val, DependsOnValue):
        return str(val)
    elif dataclasses.is_dataclass(val):
        sub_dict = dataclasses.asdict(val)  # type: ignore
        return _json_dict(sub_dict)
    elif isinstance(val, dict):
        return _json_dict(val)
    elif isinstance(val, Enum):
        return val.value
    elif isinstance(val, list):
        return [_serialize_type(i) for i in val]
    elif isinstance(val, bool):
        return str(val).lower()
    elif val is None:
        return None
    return val


def _json_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    to_ret = {}
    for key, val in d.items():
        val = _serialize_type(val)
        if val is not None:
            to_ret[key] = _serialize_type(val)
    return to_ret


@dataclasses.dataclass
class Inputs:
    def to_dict(self) -> Dict[str, Any]:
        return _json_dict(dataclasses.asdict(self))


@dataclasses.dataclass
class Outputs:
    gcp_id: Optional[str] = dataclasses.field(default=None, init=False)
    aws_arn: Optional[str] = dataclasses.field(default=None, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return _json_dict(dataclasses.asdict(self))


class DependsOnValue:
    def __init__(self, node: "Node", field_name: str, field_type: type) -> None:
        self.node = node
        self.field_name = field_name
        self.field_type = field_type

    def __repr__(self):
        return f"[yellow]Depends[/yellow]([light_goldenrod3]{self.node}[/light_goldenrod3]).{self.field_name}"


class Depends:
    _mode = "plan"  # default mode

    def __init__(self, node: "Node"):
        self.node = node
        self._outputs = None
        self._init_fields()

    def _init_fields(self):
        output_dataclass_type = self.node.outputs_type()
        for field in dataclasses.fields(output_dataclass_type):
            setattr(self, field.name, self._create_field(field.name, field.type))

    def _create_field(self, name, field_type):
        if Depends._mode == "plan":
            try:
                if self._outputs is None:
                    self._outputs = self.node.outputs()
                return getattr(self._outputs, name)
            except exceptions.ResourceOutputsNotFound:
                return DependsOnValue(self.node, name, field_type)
        elif Depends._mode == "execute":
            if self._outputs is None:
                self._outputs = self.node.outputs()
            return getattr(self._outputs, name)
        else:
            raise ValueError("Invalid mode")

    @classmethod
    def set_mode(cls, mode):
        if mode not in ("plan", "execute"):
            raise ValueError("Mode must be either 'plan' or 'execute'")
        cls._mode = mode


def mode(mode):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            previous_mode = Depends._mode
            Depends.set_mode(mode)
            try:
                result = func(*args, **kwargs)
            finally:
                Depends.set_mode(previous_mode)
            return result

        return wrapper

    return decorator


class NodeType(Enum):
    RESOURCE = "resource"
    SERVICE = "service"


T = TypeVar("T", bound=Outputs)


class Node(Generic[T]):
    def __init__(self, name: str, node_type: NodeType) -> None:
        self.name = name
        self._node_type = node_type
        self._extra_dependencies: List["Node"] = []

        # This line extracts the type argument from the Generic base
        self._outputs_type: T = get_args(self.__class__.__orig_bases__[0])[0]  # type: ignore
        if not dataclasses.is_dataclass(self._outputs_type):
            raise ValueError(
                f"Node outputs must be a dataclass, got {self._outputs_type}"
            )

    def cloud_provider(self) -> CloudProvider:
        raise NotImplementedError

    def __hash__(self):
        return hash(f"{self._node_type.value}/{self.name}")

    def inputs(self, *args, **kwargs) -> Inputs:
        raise NotImplementedError

    @mode("execute")
    def execute_inputs(self, *args, **kwargs) -> Inputs:
        return self.inputs(*args, **kwargs)

    @mode("plan")
    def plan_inputs(self, *args, **kwargs) -> Inputs:
        return self.inputs(*args, **kwargs)

    def outputs(self) -> Outputs:
        raise NotImplementedError

    async def outputs_async(self) -> Outputs:
        raise NotImplementedError

    def outputs_type(self) -> T:
        return self._outputs_type

    # This is a utility for adding dependencies to a node that are not used directly in the inputs
    def depends_on(self, *node: "Node") -> None:
        self._extra_dependencies.extend(node)

    def _rec_inputs_depend_on(self, plan: Any, depends_on: Set["Node"]):
        if not dataclasses.is_dataclass(plan):
            return
        for field in dataclasses.fields(plan):
            value = getattr(plan, field.name)
            if isinstance(value, DependsOnValue):
                depends_on.add(value.node)
            if dataclasses.is_dataclass(value):
                self._rec_inputs_depend_on(value, depends_on)

    def inputs_depend_on(self, *args, **kwargs) -> List["Node"]:
        plan = self.plan_inputs(*args, **kwargs)
        depends_on = set(self._extra_dependencies)
        self._rec_inputs_depend_on(plan, depends_on)
        return list(depends_on)

    def is_resource(self) -> bool:
        return self._node_type == NodeType.RESOURCE

    def is_service(self) -> bool:
        return self._node_type == NodeType.SERVICE
