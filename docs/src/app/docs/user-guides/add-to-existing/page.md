---
title: How to use LaunchFlow with an Existing Application
nextjs:
  metadata:
    title: How to use LaunchFlow with an Existing Application
    description: How to use LaunchFlow with an Existing Application
---

<!-- TODO check that all the code in this work, deploy seems to not -->

## Project Setup

Migrating an existing app to use LaunchFlow is easy and can be done incrementally. Let's walk through the process with a minimal FastAPI code sample on GCP.

_main.py_:
```python
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/value")
def get_value():
    return "Hello World"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Here, we have an app with one endpoint that returns a hard-coded string. It can be run by calling `python main.py`. Let's integrate LaunchFlow to use some some resources! To do so your project must contain a `launchflow.yaml` file. The simplest way to create one is by running `lf init`.

```bash
$ lf init
```

Running this command will prompt you to provide a project name and choose whether to use a local backend or LaunchFlow Cloud. Here we've chosen to use a local backend producing the following `launchflow.yaml`:

```yaml
project: use-launchflow-with-existing
backend: file://.launchflow
```

That's it!

## Add Resources

Now we can add resources and create them by running `lf create`. Let's add a Postgres database to our app.

```python,1,7+,11+
from fastapi import FastAPI
import launchflow as lf
import uvicorn

app = FastAPI()

postgres = lf.gcp.ComputeEnginePostgres("vm-postgres")

@app.get("/value")
def get_value():
    return postgres.query("SELECT 1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

We've added a Postgres database and are using it a trivial way in our endpoint. To create it, we can just run `lf create`. This command searches your codebase for LaunchFlow resources, checks to see if they've already been created (or were created with different arguments that now need updating), prompts for confirmation, then creates / updates resources in the cloud.

You'll also need to run your command using [lf run](/reference/cli#lf-run):

```bash
$ lf run YOUR_ENVIRONMENT_NAME -- python main.py
```

This command can wrap any other, and is used to configure LaunchFlow to use the correct environment. Under the hood, it runs the command in a subprocess with the environment variable `LAUNCHFLOW_ENVIRONMENT` set to the requested environment name. If you run into any problems, check that your program is able to receive it -- for example, some build systems require you to declare the environment variables you want to allow through.

After it completes, you should be good to use the Postgres instance!

## Deploy

Now that we have a working app, we can deploy it to our cloud account using LaunchFlow. The steps here are the same as for a new project:

1. Create a Dockerfile that can build and run your application.
1. Add a [Cloud Run](/reference/gcp-services/cloud-run) service to your code.
1. Run `lf deploy` on the command line.

Here's a Dockerfile that will work for our example:

```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] fastapi uvicorn

COPY ./main.py /code/main.py

ENV PORT=8080

EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

We'll add it next to our `main.py` file, and update our code to use it:

_main.py_:

```python,1,8+
from fastapi import FastAPI
import launchflow as lf
import uvicorn

app = FastAPI()

postgres = lf.gcp.ComputeEnginePostgres("vm-postgres")
cloud_run = lf.gcp.CloudRun("my-cloud-run")

@app.get("/value")
def get_value():
    return postgres.query("SELECT 1")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

The `cloud_run` service will find the Dockerfile since it's right next to our `launchflow.yaml` file, but if you want to store yours elsewhere, you can pass a path to it when creating your `CloudRun` object. That's it! Running `lf deploy` will deploy your code to cloud run.
