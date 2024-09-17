---
title: Deploy Svelte with LaunchFlow
svelte:
  metadata:
    title: Deploy Svelte with LaunchFlow
    description: Deploy Svelte to AWS / GCP with LaunchFlow
---

{% gettingStartedSelector  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Svelte application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/svelte-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Svelte application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/svelte-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Svelte application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/svelte-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Svelte application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/svelte-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}


## 0. Set up your Svelte Project

If you already have a Svelte Project you can [skip to step #1](#1-initialize-launch-flow).

---

Create a new Svelte Application

```bash
npm create svelte@latest launchflow-svelte
cd launchflow-svelte
npm install
npm install --save-dev @sveltejs/adapter-node
```

Select `Skeleton project` for a basic setup, and any other options that best suit your project needs.

---

Create a new file `src/routes/+page.server.ts` with the following contents:

```typescript
import { env } from "$env/dynamic/private";

export async function load() {
  const lfEnv = env.LAUNCHFLOW_ENVIRONMENT;
  return { props: { env: lfEnv } };
}
```

---

Update `src/routes/+page.svelte` to return a simple message:

```svelte
<script>
  export let data;
</script>

<h1>Hello from {data.props.env}</h1>
```

---

Update `svelte.config.js` to enable adapter-node:

```js
import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    adapter: adapter()
  }
};

export default config;
```

---

Create a `Dockerfile` in the root of your project:

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}
```dockerfile
FROM node:18-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV NODE_ENV=production

RUN npm prune --production

FROM node:18-alpine

WORKDIR /app

COPY --from=base /app/build build/
COPY --from=base /app/node_modules node_modules/
COPY package.json .

ENV PORT=8080
EXPOSE $PORT
CMD ["node", "build"]
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}
```dockerfile
FROM node:18-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV NODE_ENV=production

RUN npm prune --production

FROM node:18-alpine

WORKDIR /app

COPY --from=base /app/build build/
COPY --from=base /app/node_modules node_modules/
COPY package.json .

ENV PORT=80
EXPOSE $PORT
CMD ["node", "build"]
```
{% /gettingStartedSection %}


{% gettingStartedSection cloudProvider="AWS" %}
```dockerfile
FROM public.ecr.aws/docker/library/node:18-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV NODE_ENV=production

RUN npm prune --production

FROM public.ecr.aws/docker/library/node:18-alpine

WORKDIR /app

COPY --from=base /app/build build/
COPY --from=base /app/node_modules node_modules/
COPY package.json .

ENV PORT=80
EXPOSE $PORT
CMD ["node", "build"]
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}
```dockerfile
FROM node:18-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV NODE_ENV=production

RUN npm prune --production

FROM node:18-alpine

WORKDIR /app

COPY --from=base /app/build build/
COPY --from=base /app/node_modules node_modules/
COPY package.json .

ENV PORT=8080
EXPOSE $PORT
CMD ["node", "build"]
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Engine" %}
```dockerfile
FROM node:18-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

ENV NODE_ENV=production

RUN npm prune --production

FROM node:18-alpine

WORKDIR /app

COPY --from=base /app/build build/
COPY --from=base /app/node_modules node_modules/
COPY package.json .

ENV PORT=80
EXPOSE $PORT
CMD ["node", "build"]
```
{% /gettingStartedSection %}

---

## 1. Initialize Launch Flow

{% callout type="note" %}

If you're coming from a platform like Vercel you will need to:

1. Add a Dockerfile to your project as shown above.
2. Make sure your Svelte project is using the node adapter. You can do this by installing `@sveltejs/adapter-node` and updating your `svelte.config.js` as shown above.

{% /callout %}

{% lfInit /%}

---

## 2. Deploy your Service

{% deploy /%}

---

## 3. Cleanup your Resources

{% cleanup /%}

---

## 4. Visualize, Share, and Automate

{% lfcloud /%}

---

## What's next?

- View your application in the [LaunchFlow console](https://console.launchflow.com)
- Learn more about [Environments](/docs/concepts/environments), [Resources](/docs/concepts/resources), and [Services](/docs/concepts/services)
- Explore the [Resource Reference](/docs/reference/resources) to see all the resources you can create
- Join the [LaunchFlow Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ) to ask questions and get help

{% /gettingStartedSelector %}
