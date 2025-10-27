import asyncio
import kopf
import kubernetes
from kubernetes import client, config

GROUP = "sessions.example.com"
VERSION = "v1alpha1"
PLURAL = "usersessions"
KIND = "UserSession"

# Utility to build k8s api clients

def get_clients():
    config.load_incluster_config()
    api = client.CoreV1Api()
    net = client.NetworkingV1Api()
    rq = client.CoreV1Api()
    apps = client.AppsV1Api()
    crd = client.CustomObjectsApi()
    return api, net, rq, apps, crd


def ensure_namespace(name: str):
    api, *_ = get_clients()
    body = client.V1Namespace(metadata=client.V1ObjectMeta(name=name))
    try:
        api.create_namespace(body)
    except client.exceptions.ApiException as e:
        if e.status != 409:
            raise


def ensure_resource_quota(ns: str):
    api, *_ = get_clients()
    rq_name = "session-quota"
    rq_spec = client.V1ResourceQuotaSpec(hard={
        "pods": "1",
        "requests.cpu": "500m",
        "requests.memory": "512Mi",
        "limits.cpu": "1",
        "limits.memory": "1Gi",
    })
    body = client.V1ResourceQuota(metadata=client.V1ObjectMeta(name=rq_name), spec=rq_spec)
    try:
        api.create_namespaced_resource_quota(ns, body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            api.replace_namespaced_resource_quota(rq_name, ns, body)
        else:
            raise


def ensure_default_deny_network_policy(ns: str):
    _, net, *_ = get_clients()
    name = "default-deny-all"
    policy_types = ["Ingress", "Egress"]
    body = client.V1NetworkPolicy(
        metadata=client.V1ObjectMeta(name=name),
        spec=client.V1NetworkPolicySpec(
            pod_selector=client.V1LabelSelector(match_labels={}),
            policy_types=policy_types,
            ingress=[],
            egress=[],
        ),
    )
    try:
        net.create_namespaced_network_policy(ns, body)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            net.replace_namespaced_network_policy(name, ns, body)
        else:
            raise


def ensure_worker_pod(ns: str, name: str):
    api, *_ = get_clients()
    pod_name = "worker"
    labels = {"app": "user-worker", "usersession": name}
    container = client.V1Container(
        name="worker",
        image="busybox:1.36",
        command=["sh", "-c", "echo Hello from ${SESSION} && sleep 3600"],
        env=[client.V1EnvVar(name="SESSION", value=name)],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "100m", "memory": "128Mi"},
            limits={"cpu": "500m", "memory": "512Mi"},
        ),
    )
    pod = client.V1Pod(
        metadata=client.V1ObjectMeta(name=pod_name, labels=labels),
        spec=client.V1PodSpec(containers=[container], restart_policy="Never"),
    )
    try:
        api.create_namespaced_pod(ns, pod)
    except client.exceptions.ApiException as e:
        if e.status == 409:
            api.replace_namespaced_pod(pod_name, ns, pod)
        else:
            raise


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    # Optimize for cluster-wide watch of our CRD only
    settings.scanning.disabled = True
    settings.execution.max_workers = 5


@kopf.on.create(GROUP, VERSION, PLURAL)
async def on_create(body, spec, meta, status, name, logger, **kwargs):
    namespace = name  # Dedicated namespace per session
    logger.info(f"Creating environment for session {name} in namespace {namespace}")

    ensure_namespace(namespace)
    ensure_resource_quota(namespace)
    ensure_default_deny_network_policy(namespace)
    ensure_worker_pod(namespace, name)

    # Update status
    _, _, _, _, crd = get_clients()
    status_obj = {"phase": "Ready"}
    crd.patch_cluster_custom_object_status(
        GROUP, VERSION, PLURAL, name, {"status": status_obj}
    )
    logger.info("Session environment ready")


@kopf.on.delete(GROUP, VERSION, PLURAL)
async def on_delete(body, name, logger, **kwargs):
    namespace = name
    api, *_ = get_clients()
    logger.info(f"Cleaning up environment for session {name}")
    # Delete the namespace; this will remove contained resources
    propagation = client.V1DeleteOptions(propagation_policy="Foreground")
    try:
        api.delete_namespace(name=namespace, body=propagation)
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
    # Nothing else to do; CR will be removed after this handler completes
    logger.info("Cleanup requested (namespace deletion triggered)")
