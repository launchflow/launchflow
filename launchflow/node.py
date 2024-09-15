import dataclasses
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    get_args,
    get_origin,
)

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
    _outputs_cache: Dict[int, Any] = {}
    # The mode determines whether th dependencies should be resolved. There are three options:
    # - maybe_resolve (default): The dependencies are resolved if the outputs are available. If not, a DependsOnValue object is returned.
    #       - This mode is used when we are not sure if the outputs are available and we want to resolve them if they are.
    # - always_resolve: The dependencies are resolved and the outputs are returned. This will error out if the outputs are not available.
    #       - This mode is used when we are sure that the outputs are available and we want to resolve them.
    # - never_resolve: The dependencies are not resolved and the DependsOnValue object is returned.
    #      - This mode is used when we only want to know what the dependencies are without actually resolving them.
    _mode: Literal[
        "maybe_resolve", "always_resolve", "never_resolve"
    ] = "maybe_resolve"  # default mode

    def __init__(self, node: "Node"):
        self.node = node
        self._outputs = None
        self._init_fields()

    def _init_fields(self):
        output_dataclass_type = self.node._outputs_type
        for field in dataclasses.fields(output_dataclass_type):
            setattr(self, field.name, self._create_field(field.name, field.type))

    def _create_field(self, name, field_type):
        if Depends._mode == "maybe_resolve":
            cache_key = hash(self.node)
            if cache_key in self._outputs_cache:
                node_outputs = self._outputs_cache[cache_key]
                if node_outputs is not None:
                    return getattr(node_outputs, name)
                return DependsOnValue(self.node, name, field_type)
            try:
                if self._outputs is None:
                    self._outputs = self.node.outputs()
                    self._outputs_cache[cache_key] = self._outputs
                return getattr(self._outputs, name)
            except exceptions.ResourceOutputsNotFound:
                self._outputs_cache[cache_key] = None
                return DependsOnValue(self.node, name, field_type)
        elif Depends._mode == "always_resolve":
            if self._outputs is None:
                self._outputs = self.node.outputs()
            return getattr(self._outputs, name)
        elif Depends._mode == "never_resolve":
            return DependsOnValue(self.node, name, field_type)
        else:
            raise ValueError("Invalid mode")

    @classmethod
    def set_mode(cls, mode):
        if mode not in ("maybe_resolve", "always_resolve", "never_resolve"):
            raise ValueError(
                "Mode must be either 'maybe_resolve', 'always_resolve', or 'never_resolve'"
            )
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


# This function was pulled from this Stackoverflow answer:
# https://stackoverflow.com/questions/57706180/generict-base-class-how-to-get-type-of-t-from-within-instance/71720366#answer-76250220
def get_generic_map(
    base_cls: type,
    instance_cls: type,
) -> Dict[Any, Any]:
    """Get a map from the generic type paramters to the non-generic implemented types.

    Args:
        base_cls: The generic base class.
        instance_cls: The non-generic class that inherits from ``base_cls``.

    Returns:
        A dictionary mapping the generic type parameters of the base class to the
        types of the non-generic sub-class.
    """
    assert base_cls != instance_cls
    assert issubclass(instance_cls, base_cls)
    cls: Optional[type] = instance_cls
    generic_params: Tuple[Any, ...]
    generic_values: Tuple[Any, ...] = tuple()
    generic_map: Dict[Any, Any] = {}

    # Iterate over the class hierarchy from the instance sub-class back to the base
    # class and push the non-generic type paramters up through that hierarchy.
    while cls is not None and issubclass(cls, base_cls):
        if hasattr(cls, "__orig_bases__"):
            # Generic class
            bases = cls.__orig_bases__

            # Get the generic type parameters.
            generic_params = next(
                (
                    get_args(generic)
                    for generic in bases
                    if get_origin(generic) is Generic
                ),
                tuple(),
            )

            # Generate a map from the type parameters to the non-generic types pushed
            # from the previous sub-class in the hierarchy.
            generic_map = (
                {param: value for param, value in zip(generic_params, generic_values)}
                if len(generic_params) > 0
                else {}
            )

            # Use the type map to push the concrete parameter types up to the next level
            # of the class hierarchy.
            generic_values = next(
                (
                    tuple(
                        generic_map[arg] if arg in generic_map else arg
                        for arg in get_args(base)
                    )
                    for base in bases
                    if (
                        isinstance(get_origin(base), type)
                        and issubclass(get_origin(base), base_cls)
                    )
                ),
                tuple(),
            )
        else:
            generic_map = {}

        assert isinstance(cls, type)
        cls = next(
            (base for base in cls.__bases__ if issubclass(base, base_cls)),
            None,
        )

    return generic_map


class Node(Generic[T]):
    def __init__(self, name: str, node_type: NodeType) -> None:
        self.name = name
        self._node_type = node_type
        self._extra_dependencies: List["Node"] = []

        # TODO: The Resource generics are a bit of a hack. We should update them then use the generic map that the service ones use
        if node_type == NodeType.RESOURCE:
            # This line extracts the type argument from the Generic base
            self._outputs_type: Type = get_args(self.__class__.__orig_bases__[0])[0]  # type: ignore
        else:
            type_map = get_generic_map(Node, type(self))
            self._outputs_type: Type = type_map[T]  # type: ignore

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

    @mode("always_resolve")
    def execute_inputs(self, *args, **kwargs) -> Inputs:
        return self.inputs(*args, **kwargs)

    @mode("maybe_resolve")
    def plan_inputs(self, *args, **kwargs) -> Inputs:
        return self.inputs(*args, **kwargs)

    def outputs(self) -> T:
        raise NotImplementedError

    async def outputs_async(self) -> T:
        raise NotImplementedError

    # This is a utility for adding dependencies to a node that are not used directly in the inputs
    def depends_on(self, *node: "Node") -> None:
        self._extra_dependencies.extend(node)

    def _rec_inputs_depend_on(self, inputs: Any, depends_on: Set["Node"]):
        if not dataclasses.is_dataclass(inputs):
            return
        for field in dataclasses.fields(inputs):
            value = getattr(inputs, field.name)
            if isinstance(value, DependsOnValue):
                depends_on.add(value.node)
            if dataclasses.is_dataclass(value):
                self._rec_inputs_depend_on(value, depends_on)

    def inputs_depend_on(self, *args, **kwargs) -> List["Node"]:
        plan = self.plan_inputs(*args, **kwargs)
        depends_on = set(self._extra_dependencies)
        self._rec_inputs_depend_on(plan, depends_on)
        return list(depends_on)

    @mode("never_resolve")
    def dependencies(self, *args, **kwargs) -> List["Node"]:
        inputs = self.inputs(*args, **kwargs)
        depends_on = set(self._extra_dependencies)
        self._rec_inputs_depend_on(inputs, depends_on)
        return list(depends_on)

    def is_resource(self) -> bool:
        return self._node_type == NodeType.RESOURCE

    def is_service(self) -> bool:
        return self._node_type == NodeType.SERVICE
