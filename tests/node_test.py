import unittest
from dataclasses import dataclass
from unittest import mock

from launchflow.exceptions import ResourceOutputsNotFound
from launchflow.node import Depends, DependsOnValue, Inputs, Node, NodeType, Outputs


@dataclass
class ParentNodeInputs(Inputs):
    pass


@dataclass
class ParentNodeOutputs(Outputs):
    my_id: str


class ParentNode(Node[ParentNodeOutputs]):
    def __init__(self, name: str) -> None:
        super().__init__(name, NodeType.RESOURCE)

    def inputs(self, *args, **kwargs) -> ParentNodeInputs:
        return ParentNodeInputs()


@dataclass
class ChildNodeOuputs(Outputs):
    pass


@dataclass
class ChildNodeInputs(Inputs):
    parent_id: str


class ChildNode(Node[ChildNodeOuputs]):
    def __init__(self, name: str, parent: ParentNode) -> None:
        super().__init__(name, NodeType.RESOURCE)
        self.parent = parent

    def inputs(self, *args, **kwargs) -> ChildNodeInputs:
        return ChildNodeInputs(parent_id=Depends(self.parent).my_id)  # type: ignore


class NodeTest(unittest.TestCase):
    def test_parent_doesnt_exist(self):
        parent_outputs_mock = mock.MagicMock()
        parent_outputs_mock.side_effect = ResourceOutputsNotFound("parent")

        parent = ParentNode("parent")
        parent.outputs = parent_outputs_mock
        child = ChildNode("child", parent)
        with self.assertRaises(ResourceOutputsNotFound):
            child.execute_inputs()

        child_inputs = child.plan_inputs()
        self.assertIsInstance(child_inputs.parent_id, DependsOnValue)  # type: ignore

        maybe_resolved = child.inputs_depend_on()
        self.assertEqual(maybe_resolved, [parent])

        unresolved = child.dependencies()
        self.assertEqual(unresolved, [parent])

    def test_parent_exists(self):
        parent = ParentNode("parent")
        parent.outputs = mock.MagicMock()
        parent.outputs.return_value = ParentNodeOutputs(my_id="123")

        child = ChildNode("child", parent)

        execute_results = child.execute_inputs()
        self.assertEqual(execute_results.parent_id, "123")  # type: ignore

        plan_inputs = child.plan_inputs()
        self.assertEqual(plan_inputs.parent_id, "123")  # type: ignore

        maybe_resolved = child.inputs_depend_on()
        self.assertEqual(maybe_resolved, [])

        unresolved = child.dependencies()
        self.assertEqual(unresolved, [parent])


if __name__ == "__main__":
    unittest.main()
