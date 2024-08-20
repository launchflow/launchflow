from kubernetes import client


# TODO: make this async
async def deploy_new_k8s_service(
    k8_client: client.AppsV1Api,
    node_pool_id: str,
    docker_image: str,
    service_name: str,
    port: int,
    namespace: str,
):
    container = client.V1Container(
        name=service_name,
        image=docker_image,
        ports=[client.V1ContainerPort(container_port=port)],
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": service_name}),
        spec=client.V1PodSpec(
            containers=[container],
            node_selector={"nodepool": node_pool_id},
        ),
    )
    spec = client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={"matchLabels": {"app": service_name}},
    )
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=service_name),
        spec=spec,
    )
    k8_client.create_namespaced_deployment(namespace=namespace, body=deployment)

    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=service_name),
        spec=client.V1ServiceSpec(
            selector={"app": service_name},
            # TODO: should add options to expose this differently
            ports=[client.V1ServicePort(protocol="TCP", port=port, target_port=port)],
            type="LoadBalancer",
        ),
    )

    core_client = client.CoreV1Api()
    service: client.V1Service = core_client.create_namespaced_service(
        namespace=namespace, body=service
    )  # type: ignore

    print("DO NOT SUBMIT: ", service)

    # TODO: this only works for loadbalancer types
    if service.status.load_balancer.ingress:
        return (
            service.status.load_balancer.ingress[0].ip
            or service.status.load_balancer.ingress[0].hostname
        )

    return service.spec.cluster_ip


async def update_k8s_service(
    k8_client: client.AppsV1Api,
    node_pool_id: str,
    docker_image: str,
    service_name: str,
    port: int,
    namespace: str,
):
    print("DO NOT SUBMIT: update_k8s_service")
    return ""


async def destroy_k8s_service(
    service_name: str,
    namespace: str,
):
    app_client = client.AppsV1Api()
    app_client.delete_namespaced_deployment(
        name=service_name,
        namespace=namespace,
        body=client.V1DeleteOptions(),
    )

    core_client = client.CoreV1Api()
    core_client.delete_namespaced_service(
        name=service_name,
        namespace=namespace,
    )
