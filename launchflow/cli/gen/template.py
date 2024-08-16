import os
import shutil
from abc import ABC, abstractmethod
from importlib import resources
from pathlib import Path
from typing import Tuple

from jinja2 import Template


class ProjectGenerator(ABC):
    @abstractmethod
    def template_path_info(self) -> Tuple[str, str]:
        """
        Returns the package-relative path to the templates directory for this project type.
        """
        pass

    @abstractmethod
    def context(self) -> dict:
        """
        Returns the context (variables and their values) to be used in the Jinja templates.
        """
        pass

    def generate_project(self, destination_path: str):
        """
        Generate the project by rendering all Jinja templates found within the specified template directory.
        """
        # Ensure the destination directory exists
        os.makedirs(destination_path, exist_ok=True)

        template_dir, template_name = self.template_path_info()
        render_context = self.context()

        # Access the directory of the specified template
        with resources.path(template_dir, template_name) as template_dir_path:
            for root, dirs, files in os.walk(template_dir_path):
                relative_root = Path(root).relative_to(template_dir_path)
                destination_dir = Path(destination_path, relative_root)

                # Create directories in the destination path
                os.makedirs(destination_dir, exist_ok=True)

                for file in files:
                    source_path = Path(root, file)
                    destination_file_path = destination_dir / file

                    if file == "__pycache__":
                        continue

                    if file.endswith(".jinja"):
                        # Render Jinja template
                        if relative_root.name:
                            template_content = resources.read_text(
                                f"{template_dir}.{template_name}.{'.'.join(relative_root.parts)}",
                                file,
                            )
                        else:
                            template_content = resources.read_text(
                                f"{template_dir}.{template_name}", file
                            )
                        template = Template(template_content)
                        output_content = template.render(render_context) + "\n"

                        # Save the rendered file, removing the '.jinja' extension
                        destination_file_path = destination_file_path.with_suffix("")

                        with open(destination_file_path, "w") as f:
                            f.write(output_content)
                    else:
                        # Copy non-template files directly
                        shutil.copy(source_path, destination_file_path)
