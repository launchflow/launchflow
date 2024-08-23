"""Generates docs pages for the Python Client.

This script uses the `pydoc-markdown` package to generate markdown files for the Python client.

To run this script:

pip install -r requirements.txt
python main.py
"""

from collections import deque
import os
import re
import subprocess
import sys
import tempfile
from typing import Deque, Any, TextIO

import docspec
from pydoc_markdown.contrib.loaders.python import PythonLoader
from pydoc_markdown.contrib.processors.filter import FilterProcessor
from pydoc_markdown.contrib.renderers.markdown import MarkdownRenderer
from pydoc_markdown.interfaces import Context
from pydoc_markdown.util.misc import escape_except_blockquotes


KNOWN_RESOURCE_SERVICE_SUPER_CLASSES = {
    "Resource",
    "GCPResource",
    "AWSResource",
    "KubernetesResource",
    "GCPService",
    "AWSService",
}


class CustomMarkdownRenderer(MarkdownRenderer):
    def _render_recursive(self, fp: TextIO, level: int, obj: docspec.ApiObject):
        # NOTE: we override this method to sort the contents of the pages
        # We want the resources and service to be at the top
        self._render_object(fp, level, obj)
        level += 1
        members = getattr(obj, "members", [])
        sorted_members: Deque[Any] = deque()
        for member in members:
            if isinstance(member, docspec.Class):
                found_match = False
                for base in member.bases:  # type: ignore
                    result_string = re.sub(r"\[[^\]]*\]", "", base)

                    if result_string in KNOWN_RESOURCE_SERVICE_SUPER_CLASSES:
                        found_match = True
                        break
                if found_match:
                    sorted_members.appendleft(member)
                else:
                    sorted_members.append(member)
            else:
                sorted_members.append(member)

        for member in sorted_members:
            self._render_recursive(fp, level, member)

    def _render_object(self, fp: TextIO, level: int, obj: docspec.ApiObject):
        # This is not ideal because it doesn't change if other rendering settings are changed
        if isinstance(obj, docspec.Function) and obj.name == "__init__":
            if obj.docstring is None:
                return

            fp.write("### initialization\n\n")

            # Copied from the markdown renderer
            if obj.docstring:
                docstring = (
                    escape_except_blockquotes(obj.docstring.content)
                    if self.escape_html_in_docstring
                    else obj.docstring.content
                )
                lines = docstring.split("\n")
                if self.docstrings_as_blockquote:
                    lines = ["> " + x for x in lines]
                fp.write("\n".join(lines))
                fp.write("\n\n")
        else:
            super()._render_object(fp, level, obj)


_SRC_DIR = os.path.dirname(os.path.realpath(__file__)).removesuffix(
    "/scripts/docs-generator"
)
_OUTPUT_DIR = os.path.join(_SRC_DIR, "docs/src/app/reference")
_HEADER_PATTERN = re.compile(r"^#+ (`[a-zA-Z -]+`)$")

old_path = sys.path
sys.path.insert(0, _SRC_DIR)
old_dir = os.getcwd()
os.chdir(_SRC_DIR)

from launchflow.models.utils import (  # noqa: E402
    RESOURCE_PRODUCTS_TO_RESOURCES,
    SERVICE_PRODUCTS_TO_SERVICES,
)

os.chdir(old_dir)
# Don't reset the sys.path because we use it when generating the CLI docs

MODULE_TO_PAGE = {
    "launchflow.fastapi": "python-client/fastapi/page.md",
}


def add_to_module_to_page(mapping, prefix, module_to_page):
    sorted_mapping = dict(sorted(mapping.items(), key=lambda item: item[0]))
    for product, resource in sorted_mapping.items():
        if product == "unknown":
            continue

        cloud_provider = resource.cloud_provider()
        if cloud_provider is None:
            print("Skipping generating docs for", resource.__name__)
            continue

        out_path = ""
        if cloud_provider.value == "gcp":
            out_path += f"gcp-{prefix}"
        elif cloud_provider.value == "aws":
            out_path += f"aws-{prefix}"
        else:
            ValueError("Shouldn't have reached here")

        directory_name = resource.__module__.split(".")[-1].replace("_", "-")
        out_path += f"/{directory_name}/page.md"
        module_to_page[resource.__module__] = out_path


add_to_module_to_page(RESOURCE_PRODUCTS_TO_RESOURCES, "resources", MODULE_TO_PAGE)
add_to_module_to_page(SERVICE_PRODUCTS_TO_SERVICES, "services", MODULE_TO_PAGE)


# First we generate the markdown files for the Python client
context = Context(directory=".")
loader = PythonLoader(search_path=[_SRC_DIR], modules=list(MODULE_TO_PAGE.keys()))
renderer = CustomMarkdownRenderer(
    insert_header_anchors=False,
    use_fixed_header_levels=True,
    descriptive_class_title=False,
    classdef_code_block=False,
    signature_class_prefix=True,
    # signature_code_block=False,
    # signature_with_def=False,
    # signature_class_prefix=True,
    render_module_header=False,
    format_code=False,
    signature_with_def=False,
    header_level_by_type={"Module": 1, "Class": 2, "Method": 3},
)
processor = FilterProcessor(
    expression="default()",
)

loader.init(context)
processor.init(context)
renderer.init(context)

modules = loader.load()


for module in modules:
    # if module.name == "launchflow":
    #     renderer.header_level_by_type["Method"] = 2
    # else:
    #     renderer.header_level_by_type["Method"] = 3
    processor.process([module], None)
    output = renderer.render_to_string([module])
    output = output[:-1]
    output_path = os.path.join(_OUTPUT_DIR, MODULE_TO_PAGE[module.name])
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, mode="w") as f:
        f.write(output)

# Second we generate docs for the CLI

# TODO Ideally remove this, we clone a fork that doesn't abbreviate some help messages
typer_dir = tempfile.mkdtemp()
subprocess.check_call(
    [
        "git",
        "clone",
        "--branch",
        "no_abbrev_help",
        "git@github.com:mtn/typer.git",
        typer_dir,
    ]
)
sys.path.insert(0, typer_dir)

env = os.environ.copy()
env["PYTHONPATH"] = os.pathsep.join(sys.path)
docs_path = os.path.join(_SRC_DIR, "docs/src/app/reference/cli/page.md")
cli_path = os.path.join(_SRC_DIR, "launchflow/cli")
subprocess.check_call(
    [
        "typer",
        "main.py",
        "utils",
        "docs",
        "--name=lf",
        f"--output={docs_path}",
    ],
    cwd=cli_path,
    env=env,
)

sys.path = old_path

with open(docs_path, "r") as f:
    lines = f.readlines()


def replace_and_trim(match):
    content_without_backticks = match.group(2)
    return content_without_backticks


new_lines = []
for line in lines:
    match = re.match(_HEADER_PATTERN, line)
    if match:
        with_ticks = match.group(1)
        without_ticks = with_ticks[1:-1]
        line = line.replace(with_ticks, without_ticks)
    new_lines.append(line)

with open(docs_path, "w") as f:
    f.writelines(new_lines)
