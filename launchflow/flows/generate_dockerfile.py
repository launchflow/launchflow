from typing import Literal

import beaupy
from rich.console import Console

from launchflow.flows.flow_utils import ServiceRef
from launchflow.service import DockerService

DOCKERFILE_TEMPLATE = """# TODO(developer): Change the base image to match your Python version
FROM {base_image}

WORKDIR /code

# Install common dependencies since we are using a slim image
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir {extra_pip_packages}

# TODO(developer): Uncomment the following lines if you need to install additional dependencies
# COPY ./requirements.txt /code/requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# TODO(developer): Only copy the files needed for your application
COPY . /code

# Expose the port for the FastAPI app
ENV PORT={port}
EXPOSE $PORT

# TODO(developer): Change the command to match your application
CMD {command}
"""


def fastapi_dockerfile_template(
    gcp_or_aws: Literal["gcp", "aws"], base_image: str, port: int, fastapi_path: str
):
    return DOCKERFILE_TEMPLATE.format(
        base_image=base_image,
        extra_pip_packages=f"fastapi uvicorn launchflow[{gcp_or_aws}]",
        port=port,
        command=f"uvicorn {fastapi_path} --host 0.0.0.0 --port $PORT",
    )


def django_dockerfile_template(
    gcp_or_aws: Literal["gcp", "aws"], base_image: str, port: int, django_path: str
):
    return DOCKERFILE_TEMPLATE.format(
        base_image=base_image,
        extra_pip_packages=f"django gunicorn launchflow[{gcp_or_aws}]",
        port=port,
        command=f"exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 {django_path}",
    )


def flask_dockerfile_template(
    gcp_or_aws: Literal["gcp", "aws"], base_image: str, port: int, flask_path: str
):
    return DOCKERFILE_TEMPLATE.format(
        base_image=base_image,
        extra_pip_packages=f"flask gunicorn launchflow[{gcp_or_aws}]",
        port=port,
        command=f"exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 {flask_path}",
    )


def vanilla_python_dockerfile_template(
    gcp_or_aws: Literal["gcp", "aws"], base_image: str, port: int
):
    return DOCKERFILE_TEMPLATE.format(
        base_image=base_image,
        extra_pip_packages=f"launchflow[{gcp_or_aws}]",
        port=port,
        command="python -m http.server $PORT",
    )


def generate_dockerfile(
    service: DockerService,
    gcp_or_aws: Literal["gcp", "aws"],
    console: Console = Console(),
):
    if gcp_or_aws == "gcp":
        base_image = "python:3.11-slim"
        port = 8080
    else:
        base_image = "public.ecr.aws/docker/library/python:3.11-slim"
        port = 80

    # prompt the user to generate a Dockerfile
    # or incremenet the missing dockerfile count
    generate = beaupy.confirm(
        f"Would you like to generate a Dockerfile for {ServiceRef(service)}?",
    )
    if generate:
        console.print("Select the Dockerfile template you would like to generate:")
        template = beaupy.select(
            [
                "FastAPI",
                "Django",
                "Flask",
                "Vanilla Python",
            ],
        )
        if template == "FastAPI":
            fast_api_path = beaupy.prompt(
                "Enter the path to the FastAPI app",
                # TODO: Use ast to find a better default value
                initial_value="main:app",
            )
            if not fast_api_path:
                return False
            with open(service.dockerfile, "w") as f:
                f.write(
                    fastapi_dockerfile_template(
                        gcp_or_aws, base_image, port, fast_api_path
                    )
                )
            console.print(
                f"Generated Dockerfile for {ServiceRef(service)} using FastAPI template."
            )
            return True
        elif template == "Django":
            django_path = beaupy.prompt(
                "Enter the path to the Django WSGI app",
                # TODO: Use ast to find a better default value
                initial_value="myproject.wsgi:application",
            )
            if not django_path:
                return False
            with open(service.dockerfile, "w") as f:
                f.write(
                    django_dockerfile_template(
                        gcp_or_aws, base_image, port, django_path
                    )
                )
            console.print(
                f"Generated Dockerfile for {ServiceRef(service)} using Django template."
            )
            return True
        elif template == "Flask":
            flask_path = beaupy.prompt(
                "Enter the path to the Flask app",
                # TODO: Use ast to find a better default value
                initial_value="app:app",
            )
            if not flask_path:
                return False
            with open(service.dockerfile, "w") as f:
                f.write(
                    flask_dockerfile_template(gcp_or_aws, base_image, port, flask_path)
                )
            console.print(
                f"Generated Dockerfile for {ServiceRef(service)} using Flask template."
            )
            return True
        elif template == "Vanilla Python":
            with open(service.dockerfile, "w") as f:
                f.write(
                    vanilla_python_dockerfile_template(gcp_or_aws, base_image, port)
                )
            console.print(
                f"Generated Dockerfile for {ServiceRef(service)} using Vanilla Python template."
            )
            return True

    return False
