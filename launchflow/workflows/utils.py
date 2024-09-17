import io
import os
import random
import tarfile
import tempfile
import zipfile
from typing import IO, Generator, List, Optional, Union

from pathspec import PathSpec

from launchflow.workflows.commands.tf_commands import TFCommand


# NOTE: The first time this generator is called, it will yield the base_name. Every
# time after that, it will yield the base_name with a random number appended to it.
def unique_resource_name_generator(
    base_name: str, join_str: str = "-", max_length: Optional[int] = None
) -> Generator[str, None, None]:
    rand_value = None
    if max_length is not None and len(base_name) > max_length:
        base_name = base_name[:max_length]
    while True:
        if rand_value is None:
            yield base_name
        else:
            # NOTE: the default join_str is a dash, so the default output will be
            # something like "my-resource-1234"
            random_addition = f"{join_str}{rand_value}"
            if max_length is not None:
                # NOTE: if the max_length is set, we need to make sure the random
                # addition doesn't exceed it
                if len(base_name) + len(random_addition) > max_length:
                    base_name = base_name[: max_length - len(random_addition)]
            yield f"{base_name}{random_addition}"

            yield f"{base_name}{join_str}{rand_value}"
        rand_value = random.randint(1000, 9999)


# TODO: fix type hints so the outputs are correct (destroy returns bool, apply returns outputs)
async def run_tofu(command: TFCommand):
    with tempfile.TemporaryDirectory() as tempdir:
        return await command.run(tempdir)


DEFAULT_IGNORE_PATTERNS = [
    "*.log",
    "__pycache__/",
    ".env",
    ".git/",
    ".terraform/",
]


def tar_source_in_memory(directory: str, ignore_patterns: List[str]):
    ignore_patterns = list(set(ignore_patterns + DEFAULT_IGNORE_PATTERNS))

    def should_include_file(pathspec: PathSpec, file_path: str, root_dir: str):
        relative_path = os.path.relpath(file_path, root_dir)
        return not pathspec.match_file(relative_path)

    pathspec = PathSpec.from_lines("gitwildmatch", ignore_patterns)

    # Use BytesIO object as an in-memory file
    in_memory_tar = io.BytesIO()

    # Open the tarfile using the in-memory file-like object
    with tarfile.open(fileobj=in_memory_tar, mode="w:gz") as tar:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if should_include_file(pathspec, file_path, directory):
                    tar.add(file_path, arcname=os.path.relpath(file_path, directory))

    # Seek to the beginning of the in-memory file
    in_memory_tar.seek(0)

    # Return the in-memory file
    return in_memory_tar


def zip_source(
    directory: str,
    ignore_patterns: List[str],
    file: Union[str, IO[bytes]] = io.BytesIO(),
):
    ignore_patterns = list(set(ignore_patterns + DEFAULT_IGNORE_PATTERNS))

    def should_include_file(pathspec: PathSpec, file_path: str, root_dir: str):
        relative_path = os.path.relpath(file_path, root_dir)
        return not pathspec.match_file(relative_path)

    pathspec = PathSpec.from_lines("gitwildmatch", ignore_patterns)

    with zipfile.ZipFile(file, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if should_include_file(pathspec, file_path, directory):
                    zipf.write(file_path, os.path.relpath(file_path, directory))

    if isinstance(file, str):
        return file

    # Seek to the beginning of the in-memory file
    file.seek(0)
    return file
