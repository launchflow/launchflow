import ast
import importlib
import logging
import os
from typing import Dict, List, Literal

from launchflow.resource import Resource
from launchflow.service import Service

# TODO: add primitive ones here.
# NOTE: We do this to ensure we don't trigger imports in files we don't need to.
# For instance if someone uses `launchflow.fastapi` in a file, we don't want to
# execute that file.
KNOWN_IMPORT_PATHS = [
    "launchflow.gcp",
    "launchflow.kubernetes",
    "launchflow.aws",
    "launchflow.docker",
    "launchflow",
]


def _is_launchflow_entity(import_path: str) -> bool:
    maybe_entity = False
    for known_import in KNOWN_IMPORT_PATHS:
        if known_import in import_path:
            maybe_entity = True
            break
    if not maybe_entity:
        return False
    split_path = import_path.split(".")
    resource_name = split_path[-1]

    # This checks if the resource_name starts with a lowercase character to act as a
    # proxy check for the resource being a class. This is not foolproof but should
    # filter out most utility functions.
    if resource_name[0].islower():
        return False
    return maybe_entity


def _is_launchflow_resource(import_path: str) -> bool:
    if not _is_launchflow_entity(import_path):
        return False
    split_path = import_path.split(".")
    resource_name = split_path[-1]
    module = ".".join(split_path[:-1])
    module_type = importlib.import_module(module)

    if hasattr(module_type, resource_name) and (
        issubclass(getattr(module_type, resource_name), Resource)
    ):
        return True
    return False


def _is_launchflow_service(import_path: str) -> bool:
    if not _is_launchflow_entity(import_path):
        return False
    split_path = import_path.split(".")
    service_name = split_path[-1]
    module = ".".join(split_path[:-1])
    module_type = importlib.import_module(module)

    if hasattr(module_type, service_name) and issubclass(
        getattr(module_type, service_name), Service
    ):
        return True
    return False


class LaunchFlowAssignmentVisitor(ast.NodeVisitor):
    def __init__(self, scan_type: Literal["resources", "services"]):
        super().__init__()
        self.launchflow_imported_names: Dict[str, str] = {}
        self.launchflow_vars: List[str] = []
        self.nesting_level = 0
        self.scan_type = scan_type
        self.current_file = ""

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == "launchflow":
                self.launchflow_imported_names[
                    alias.asname if alias.asname else alias.name
                ] = "launchflow"

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module is not None and "launchflow" in node.module:
            for alias in node.names:
                full_name = f"{node.module}.{alias.name}"
                self.launchflow_imported_names[
                    alias.asname if alias.asname else alias.name
                ] = full_name
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Increase nesting level when entering a function
        self.nesting_level += 1
        self.generic_visit(node)  # Visit children
        # Decrease nesting level when leaving a function
        self.nesting_level -= 1

    def visit_AsyncFunctionDef(self, node):
        # Handle async functions similarly to regular functions
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_ClassDef(self, node):
        # Increase nesting level when entering a class
        self.nesting_level += 1
        self.generic_visit(node)  # Visit children
        # Decrease nesting level when leaving a class
        self.nesting_level -= 1

    def visit_Assign(self, node):
        # Check to ensure the resource was assigned to a variable.
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            return
        # Check to ensure the value is a call to a function
        if not isinstance(node.value, ast.Call):
            return

        assigned_var = node.targets[0].id
        call_name = None
        if isinstance(node.value.func, ast.Name):
            call_name = self.launchflow_imported_names.get(node.value.func.id)
        elif isinstance(node.value.func, ast.Attribute):
            call_name = self._reconstruct_full_name(node.value.func)
        else:
            return
        if call_name:
            if (
                self.scan_type == "resources" and _is_launchflow_resource(call_name)
            ) or (self.scan_type == "services" and _is_launchflow_service(call_name)):
                if self.nesting_level != 0:
                    resource_name = "UNKNOWN"
                    if len(node.value.args) != 0:
                        resource_name = node.value.args[0]
                        if isinstance(resource_name, ast.Constant):
                            resource_name = resource_name.value
                    else:
                        # fetch the name attribute from kwargs
                        for kwarg in node.value.keywords:
                            if kwarg.arg == "name":
                                resource_name = kwarg.value
                                if isinstance(resource_name, ast.Constant):
                                    resource_name = resource_name.value
                    full_call = f"{call_name}({resource_name})"
                    logging.error(
                        "%s is not defined as a global variable and will be ignored. Defined at: %s:%d",
                        full_call,
                        self.current_file,
                        node.lineno,
                    )
                    return
                self.launchflow_vars.append(assigned_var)

    def _reconstruct_full_name(self, node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name) and node.id in self.launchflow_imported_names:
            parts.append(self.launchflow_imported_names[node.id])
        else:
            return None
        parts.reverse()
        return ".".join(parts)


def find_launchflow_resources(
    directory: str, ignore_roots: List[str] = []
) -> List[str]:
    roots_to_ignore = set(ignore_roots)
    to_scan = []
    for root, dirs, files in os.walk(directory):
        root_name = os.path.basename(root)
        if root_name in roots_to_ignore:
            logging.debug(f"Ignoring root directory: {root_name}")
            dirs.clear()  # NOTE: This prevents os.walk from traversing the directory
            continue
        for file in files:
            if file.endswith(".py"):
                to_scan.append(os.path.join(root, file))
    return _scan_for(to_scan, root=directory, scan_type="resources")


def find_launchflow_services(directory: str, ignore_roots: List[str] = []) -> List[str]:
    roots_to_ignore = set(ignore_roots)
    to_scan = []
    for root, dirs, files in os.walk(directory):
        root_name = os.path.basename(root)
        if root_name in roots_to_ignore:
            logging.debug(f"Ignoring root directory: {root_name}")
            dirs.clear()  # NOTE: This prevents os.walk from traversing the directory
            continue
        for file in files:
            if file.endswith(".py"):
                to_scan.append(os.path.join(root, file))
    return _scan_for(to_scan, root=directory, scan_type="services")


def _scan_for(files: List[str], root: str, scan_type: Literal["resources", "services"]):
    entity_imports = []
    for file_path in files:
        with open(file_path, "r") as f:
            file_contents = f.read()
        tree = ast.parse(file_contents)
        finder = LaunchFlowAssignmentVisitor(scan_type=scan_type)
        finder.current_file = file_path
        finder.visit(tree)
        base_module_path = (
            os.path.relpath(file_path, root)[:-3].split(os.path.sep)
            if file_path.endswith(".py")
            else os.path.relpath(file_path, root).split(os.path.sep)
        )
        module_path = ".".join(base_module_path)
        for var in finder.launchflow_vars:
            entity_imports.append(f"{module_path}:{var}")
    return entity_imports
