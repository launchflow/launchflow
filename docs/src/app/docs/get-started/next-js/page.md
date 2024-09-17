---
title: Deploy Next.js with LaunchFlow
nextjs:
  metadata:
    title: Deploy Next.js with LaunchFlow
    description: Deploy Next.js to AWS / GCP with Launchflow
---

{% gettingStartedSelector awsRuntimeOptions=["ECS Fargate"]  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Next.js application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/next-js-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Next.js application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/next-js-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Next.js application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/next-js-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Next.js application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/next-js-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}


## 0. Set up your Next.js Project

If you already have a Next.js Project you can [skip to step #1](#1-initialize-launch-flow).

---

Create a new Next.js Application

```bash
npx create-next-app@latest launchflow-nextjs
cd launchflow-nextjs
```

Select all the default options.

---

Update `src/app/page.tsx` to return a simple message:

```tsx
import { unstable_noStore as noStore } from "next/cache";

export default function Home() {
  // We use noStore here to allow us dynamic access of runtime environment variables (e.g. process.env.LAUNCHFLOW_ENVIRONMENT).
  // If you don't need this feature you should remove this.
  // See: https://nextjs.org/docs/app/building-your-application/configuring/environment-variables#runtime-environment-variables
  noStore();
  return <div>Hello from {process.env.LAUNCHFLOW_ENVIRONMENT}</div>;
}
```

---

Update `next.config.mjs` to output a standalone build:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

export default nextConfig;
```

---

Create a `Dockerfile` in the root of your project:

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

```dockerfile
FROM node:18-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile; \
  else echo "Lockfile not found." && exit 1; \
  fi

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN \
  if [ -f yarn.lock ]; then yarn run build; \
  elif [ -f package-lock.json ]; then npm run build; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm run build; \
  else echo "Lockfile not found." && exit 1; \
  fi

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# NOTE: You may need to add this back if you have a public directory
# COPY --from=builder /app/public ./public

RUN mkdir .next
RUN chown nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080
ENV PORT=8080

ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

```dockerfile
FROM node:18-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile; \
  else echo "Lockfile not found." && exit 1; \
  fi

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN \
  if [ -f yarn.lock ]; then yarn run build; \
  elif [ -f package-lock.json ]; then npm run build; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm run build; \
  else echo "Lockfile not found." && exit 1; \
  fi

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# NOTE: You may need to add this back if you have a public directory
# COPY --from=builder /app/public ./public

RUN mkdir .next
RUN chown nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080
ENV PORT=8080

ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

{% /gettingStartedSection %}


{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

```dockerfile
FROM node:18-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN \
    if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
    elif [ -f package-lock.json ]; then npm ci; \
    elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile; \
    else echo "Lockfile not found." && exit 1; \
    fi

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN \
    if [ -f yarn.lock ]; then yarn run build; \
    elif [ -f package-lock.json ]; then npm run build; \
    elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm run build; \
    else echo "Lockfile not found." && exit 1; \
    fi

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN apk add --no-cache libcap
RUN setcap 'cap_net_bind_service=+ep' /usr/local/bin/node
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# NOTE: You may need to add this back if you have a public directory
# COPY --from=builder /app/public ./public

RUN mkdir .next
RUN chown nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 80
ENV PORT=80

ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

{% /gettingStartedSection %}


{% gettingStartedSection cloudProvider="AWS" %}

```dockerfile
FROM public.ecr.aws/docker/library/node:18-alpine AS base

FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

COPY package.json yarn.lock* package-lock.json* pnpm-lock.yaml* ./
RUN \
  if [ -f yarn.lock ]; then yarn --frozen-lockfile; \
  elif [ -f package-lock.json ]; then npm ci; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm i --frozen-lockfile; \
  else echo "Lockfile not found." && exit 1; \
  fi

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN \
  if [ -f yarn.lock ]; then yarn run build; \
  elif [ -f package-lock.json ]; then npm run build; \
  elif [ -f pnpm-lock.yaml ]; then corepack enable pnpm && pnpm run build; \
  else echo "Lockfile not found." && exit 1; \
  fi

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN apk add --no-cache libcap
RUN setcap 'cap_net_bind_service=+ep' /usr/local/bin/node
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# NOTE: You may need to add this back if you have a public directory
# COPY --from=builder /app/public ./public

RUN mkdir .next
RUN chown nextjs:nodejs .next

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 80
ENV PORT=80

ENV HOSTNAME="0.0.0.0"
CMD ["node", "server.js"]
```

{% /gettingStartedSection %}

---



## 1. Initialize Launch Flow

{% callout type="note" %}

If you're coming from a platform like Vercel you will need update two things:

1. Add a Dockerfile to your project. If you don't have a Dockerfile you can [get started with Next.js's recommended Dockerfile](https://github.com/vercel/next.js/blob/canary/examples/with-docker/Dockerfile).
2. Make sure your Next.js project is set to [output a standalone build](https://nextjs.org/docs/app/api-reference/next-config-js/output). You can do this by adding `output: "standalone"` to your `next.config.mjs`:

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

{% whatsnext /%}

{% /gettingStartedSelector %}
