---
title: Add Resources to your Application
nextjs:
  metadata:
    title: Add Resource to your Application
    description: Add Resource to your Application
---

LaunchFlow can create and manage resources for you. These resources are guaranteed to be accessible by your application running in the same environment.

---

To define resource simply declare a variable of the resource type you want in your infra.py. For example, to add a bucket you can do:

```python
import launchflow as lf

gcs_bucket = lf.gcp.GCSBucket("my-bucket")
```

---

To create your bucket run:

```bash
lf create
```

Any services you have running will now have access to read and write to that bucket automatically.

---

A full list of AWS and GCP resources can be found in the [reference docs](/reference).
