---
title: Resources
nextjs:
  metadata:
    title: Resources
    description: LaunchFlow Resources
---

<!-- TODO update and test code samples -->
<!-- TODO replace this image with the new one from the landing page -->
{% mdimage src="/images/resources_light.svg" alt="diagram" className="block dark:hidden" height=250 width=600 /%}
{% mdimage src="/images/resources_dark.svg" alt="diagram" className="hidden dark:block" height=250 width=600 /%}

## Overview

Resources allow you to add databases, cloud storage, task queues, and more to your application by simply importing them in your code. They unify **managing** infrastructure in your cloud account and **using** it in your code.

To create infrastructure, import the LaunchFlow resource, use it in your code, and run `lf create` on the command line. Then,

- Make updates to the its configuration by updating the object in your code and running `lf create` again
- Use utility methods or the underlying cloud clients to interface with it
- Delete it by running the `lf destroy` command

<!-- TODO add a gcp / aws toggle for this -->

{% tabProvider defaultLabel="GCP" %}
{% tabs %}
{% tab label="GCP" %}
```python
import launchflow as lf

# Create / Connect to a Postgres Cluster on CloudSQL
postgres = lf.gcp.CloudSQLPostgres("postgres-cluster", disk_size=10, tier="db-f1-micro")

if __name__ == "__main__":
    # Built-in utility methods for working with Postgres
    postgres.query("SELECT * FROM my_table")

    # Built-in connectors for common ORMs
    postgres.sqlalchemy_engine()
    postgres.django_settings()

    # Async support
    postgres.sqlalchemy_async_engine()
```
{% /tab %}
{% tab label="AWS" %}
```python
import launchflow as lf

# Create / Connect to a Postgres Cluster on RDS
postgres = lf.aws.RDSPostgres("postgres-cluster", allocated_storage=10, instance_class="db.t2.micro")

if __name__ == "__main__":
    # Built-in utility methods for working with Postgres
    postgres.query("SELECT * FROM my_table")

    # Built-in connectors for common ORMs
    postgres.sqlalchemy_engine()
    postgres.django_settings()

    # Async support
    postgres.sqlalchemy_async_engine()
```
{% /tab %}
{% /tabs %}
{% /tabProvider %}

For more comprehensive examples, see the [Get Started Guide](/docs/get-started).

For a full list of resources, see the [Reference Documentation](/reference).

## CLI Commands

### Create Resources

```bash
lf create
```

### Delete Resources

```bash
lf destroy
```

### List Resources

```bash
lf resources list
```

For a full list of options see the command references:

- [lf create](/reference/cli#launchflow-create)
- [lf destroy](/reference/cli#launchflow-destroy)
- [lf resources](/reference/cli#launchflow-resources)
