---
title: Deploy Golang with LaunchFlow
nextjs:
  metadata:
    title: Deploy Golang with LaunchFlow
    description: Deploy Golang applications to AWS / GCP with LaunchFlow
---

{% gettingStartedSelector awsRuntimeOptions=["ECS Fargate"]  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Go application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/go-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Go application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/go-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Go application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/go-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Go application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/go-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}

## 0. Set up your Go Project

If you already have a Go Project you can [skip to step #1](#1-initialize-launch-flow).

---

Initialize your Go module:

```bash
mkdir launchflow-go
cd launchflow-go
go mod init launchflow-go
```

---

Create a `main.go` file with a simple HTTP server:

```go
package main

import (
    "fmt"
    "log"
    "net/http"
    "os"
)

func main() {
    lfEnv := os.Getenv("LAUNCHFLOW_ENVIRONMENT")
    if lfEnv == "" {
        log.Fatal("LaunchFlow environment not set")
    }
    port := os.Getenv("PORT")
    if port == "" {
        port = "3000"
    }
    host := os.Getenv("HOST")
    if host == "" {
        host = "127.0.0.1"
    }
    address := fmt.Sprintf("%s:%s", host, port)

    greeting := fmt.Sprintf("Hello from %s!", lfEnv)
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprint(w, greeting)
    })

    log.Printf("Server listening on %s", address)
    log.Fatal(http.ListenAndServe(address, nil))
}
```

---

Create a `Dockerfile` in the root directory of your project:

{% gettingStartedSection cloudProvider="AWS" %}
```dockerfile
FROM public.ecr.aws/docker/library/golang:1.20 as builder

WORKDIR /app
COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /go/bin/app

FROM public.ecr.aws/docker/library/alpine:3.14

COPY --from=builder /go/bin/app /go/bin/app

ENV HOST=0.0.0.0
ENV PORT=80

ENTRYPOINT ["/go/bin/app"]
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}
```dockerfile
FROM golang:1.20 as builder

WORKDIR /app
COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /go/bin/app

FROM alpine:3.14

COPY --from=builder /go/bin/app /go/bin/app

ENV HOST=0.0.0.0
ENV PORT=8080

ENTRYPOINT ["/go/bin/app"]
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}
```dockerfile
FROM golang:1.20 as builder

WORKDIR /app
COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /go/bin/app

FROM alpine:3.14

COPY --from=builder /go/bin/app /go/bin/app

ENV HOST=0.0.0.0
ENV PORT=80

ENTRYPOINT ["/go/bin/app"]
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}
```dockerfile
FROM golang:1.20 as builder

WORKDIR /app
COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /go/bin/app

FROM alpine:3.14

COPY --from=builder /go/bin/app /go/bin/app

ENV HOST=0.0.0.0
ENV PORT=8080

ENTRYPOINT ["/go/bin/app"]
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

{% whatsnext /%}

{% /gettingStartedSelector %}
