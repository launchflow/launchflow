---
title: Spring Boot with LaunchFlow
springboot:
  metadata:
    title: Spring Boot with LaunchFlow
    description: Deploy Spring Boot to AWS / GCP with LaunchFlow
---

{% gettingStartedSelector  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Spring Boot application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/spring-boot-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Spring Boot application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/spring-boot-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Spring Boot application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/spring-boot-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Spring Boot application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/spring-boot-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}


## 0. Set up your Spring Boot Project

If you already have a Spring Boot Project you can [skip to step #1](#1-initialize-launch-flow).

---

Create a new Spring Boot Application

```bash
spring init --dependencies=web launchflow-springboot
cd launchflow-springboot
```

---

Update `src/main/java/com/example/demo/DemoApplication.java` to include a simple REST controller:

```java
package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
@RestController
public class DemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }

    @GetMapping("/")
    public String hello() {
        return "Hello from " + System.getenv("LAUNCHFLOW_ENVIRONMENT");
    }
}
```

---

Create a `Dockerfile` in the root of your project:

```dockerfile
FROM openjdk:17-jdk-slim as build
WORKDIR /workspace/app

COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .
COPY src src

RUN ./mvnw install -DskipTests
RUN mkdir -p target/dependency && (cd target/dependency; jar -xf ../*.jar)

FROM openjdk:17-jdk-slim
VOLUME /tmp
ARG DEPENDENCY=/workspace/app/target/dependency
COPY --from=build ${DEPENDENCY}/BOOT-INF/lib /app/lib
COPY --from=build ${DEPENDENCY}/META-INF /app/META-INF
COPY --from=build ${DEPENDENCY}/BOOT-INF/classes /app
ENTRYPOINT ["java","-cp","app:app/lib/*","com.example.demo.DemoApplication"]
```

---

## 1. Initialize Launch Flow

{% callout type="note" %}

If you're coming from a different platform, ensure you have a Dockerfile in your project that builds and runs your Spring Boot application.

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
