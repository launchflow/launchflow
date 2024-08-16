---
title: Why LaunchFlow
nextjs:
  metadata:
    title: Why LaunchFlow
    description: LaunchFlow is a complete infrastructure toolkit for Python developers. It provides a simple and consistent interface for managing infrastructure across multiple cloud providers.
---

## Simple, Secure, Built for Teams

### Infrastructure as Code isn't Enough

Infrastructure as Code (IaC) makes managing infrastructure easier and repeatable by bringing infrastructure definitions into code. This code can be versioned, reviewed, and tested just like any other. However, IaC is only one part of the solution - you also need to handle things like configuring multiple environments, access control, release pipelines, secrets, monitoring, and other operational concerns.

LaunchFlow provides customizable modules for GCP, AWS, and Docker that are configured for multi-environment support, easy release pipelines, and team sharing by default. These infrastructure types plug into a set of CLI tools that help Python developers manage and collaborate on their infrastructure in a way that is simple, secure, and always centered around their code.

## The LaunchFlow Toolkit

### Resources, Services, and Environments

LaunchFlow's abstractions help you manage your infrastructure:

- [Resouces](/docs/concepts/resources) make it easy to provision cloud resources and connect to them in your code, regardless of where it's running from
- [Services](/docs/concepts/services) decrease the overhead of setting up and managing release pipelines
- [Environments](/docs/concepts/environments) group resources and services together so you can test, stage, and deploy your code easily

### Tools for Local Development and Collaboration

- The LaunchFlow CLI allows you to manage your infrastructure from the command line. It can be used to create, update, and destroy infrastructure, as well as manage secrets, access control, and more.

- The LaunchFlow Web Console is a web-based interface that allows you to manage your infrastructure from anywhere. It provides a simple and intuitive way to view and manage your infrastructure and collaborate with your team.

- LaunchFlow state can be stored in a local file for quick experimentation, or shared with teammates via LaunchFlow Cloud.
