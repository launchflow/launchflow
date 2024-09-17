---
title: Promote your Application to new Environments
nextjs:
  metadata:
    title: Promote your Application to new Environments
    description: Promote your Application to new Environments
---

Once you have your application running in a development environment, you can promote it to other environments such as staging and production. In this guide we'll assume you have a `dev` environment that you want to promote to a new environment name `prod`.

---

First duplicate your stack to your new environment:

```bash
lf create prod
```

This will create production copies of all of your infrastructure in your `prod` environment.

---

Next, you can promote your application to the new environment:

```bash
lf promote dev prod
```

This command will prompt you to select which services to promote. When you select a service we will copy the currently running version in `dev` to `prod`.

Now you have a production ready application! From now on if you don't have any new infrastructure that needs to be created or updated you can simply run `lf promote`.
