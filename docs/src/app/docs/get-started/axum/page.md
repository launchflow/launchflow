---
title: Deploy Axum with LaunchFlow
nextjs:
  metadata:
    title: Deploy Axum with LaunchFlow
    description: Deploy Axum to AWS / GCP with Launchflow
---

{% gettingStartedSelector  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Axum application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/axum-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Axum application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/axum-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Axum application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/axum-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Axum application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/axum-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}



## 0. Set up your Axum Project

If you already have a Axum Project you can [skip to step #1](#1-initialize-launch-flow).

---

Initialize your crate:

```bash
cargo new launchflow-axum
cd launchflow-axum
cargo add axum
cargo add tokio -F full
```

---

Update `src/main.rs` to have a simple handler:

```rust
use axum::{routing::get, Router};

#[tokio::main]
async fn main() {
    let lf_env = std::env::var("LAUNCHFLOW_ENVIRONMENT").expect("LaunchFlow environment not set");
    let port = std::env::var("PORT").unwrap_or("3000".to_string());
    let host = std::env::var("HOST").unwrap_or("0.0.0.0".to_string());
    let address = format!("{host}:{port}");

    let greeting = format!("Hello from {lf_env}!");
    let app = Router::new().route("/", get(|| async { greeting }));

    let listener = tokio::net::TcpListener::bind(address).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

---

Create a `Dockerfile` in the root directory of your create.

{% gettingStartedSection cloudProvider="AWS" %}
```dockerfile
FROM public.ecr.aws/docker/library/rust:1.71 as builder

WORKDIR /app
COPY . .

RUN cargo build --release --bin launchflow-axum

FROM public.ecr.aws/docker/library/debian:bullseye AS runtime

WORKDIR /app
COPY --from=builder /app/target/release/launchflow-axum /usr/local/bin

ENV HOST=0.0.0.0
ENV PORT=80

ENTRYPOINT ["/usr/local/bin/launchflow-axum"]
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

```dockerfile
FROM rust:1.71 as builder

WORKDIR /app
COPY . .

RUN cargo build --release --bin launchflow-axum

FROM debian:bullseye AS runtime

WORKDIR /app
COPY --from=builder /app/target/release/launchflow-axum /usr/local/bin

ENV HOST=0.0.0.0
ENV PORT=8080

ENTRYPOINT ["/usr/local/bin/launchflow-axum"]
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

```dockerfile
FROM rust:1.71 as builder

WORKDIR /app
COPY . .

RUN cargo build --release --bin launchflow-axum

FROM debian:bullseye AS runtime

WORKDIR /app
COPY --from=builder /app/target/release/launchflow-axum /usr/local/bin

ENV HOST=0.0.0.0
ENV PORT=80

ENTRYPOINT ["/usr/local/bin/launchflow-axum"]
```

{% /gettingStartedSection %}
{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

```dockerfile
FROM rust:1.71 as builder

WORKDIR /app
COPY . .

RUN cargo build --release --bin launchflow-axum

FROM debian:bullseye AS runtime

WORKDIR /app
COPY --from=builder /app/target/release/launchflow-axum /usr/local/bin

ENV HOST=0.0.0.0
ENV PORT=8080

ENTRYPOINT ["/usr/local/bin/launchflow-axum"]
```
{% /gettingStartedSection %}
---

## 1. Initialize Launch Flow

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

<!-- - Checkout out our [example applications](/examples) to see even more way to use LaunchFlow. -->

{% /gettingStartedSelector %}
