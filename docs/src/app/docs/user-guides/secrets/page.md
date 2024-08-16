---
title: Secrets
nextjs:
  metadata:
    title: Secrets
    description: Using LaunchFlow Secrets
---

LaunchFlow secrets allow you to easily reference sensitive information such as API keys, passwords, and private keys in your code without exposing them in your codebase.

{% tabProvider defaultLabel="GCP" %}

{% tabs %}
{% tab label="GCP" %}

For GCP LaunchFlow Environments, you can use [launchflow.gcp.SecretManagerSecret](/reference/gcp-resources/secret-manager) to create a secret:


```python
import launchflow as lf

api_key = lf.gcp.SecretManagerSecret("api-key")
```


{% /tab %}

{% tab label="AWS" %}

For AWS LaunchFlow Environments, you can use [launchflow.aws.SecretsManagerSecret](/reference/aws-resources/secrets-manager) to create a secret:


```python
import launchflow as lf

api_key = lf.aws.SecretsManagerSecret("api-key")
```

{% /tab %}

{% /tabs %}

{% endtabProvider %}

Then run `lf create` to create the container for your secret. Once the container is created, you can set the value with the [lf secrets set](/reference/cli#launchflow-secrets-set) CLI command:

```bash
lf secrets set api-key <secret-value>
```

Once you've run this you can access the secret in your code by calling the `version` method on the secret object.

```python
from app.infra import api_key

api_key.version()
```

In addition to using the `lf secrets set` method you can also set versions directly in the AWS or GCP console, or use the `add_version` method of your secrets resource.

```python
from app.infra import api_key

api_key.add_version("my-api-key")
```
