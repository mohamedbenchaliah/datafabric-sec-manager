import argparse
import logging

from kubernetes import client, config
from kubernetes.client.rest import ApiException

POD_SUCCEEDED = "succeeded"
POD_FAILED = "failed"
POD_REASON_EVICTED = "evicted"
POD_RESTART_POLICY_NEVER = "never"


def delete_pod(name, namespace):
    core_v1 = client.CoreV1Api()
    delete_options = client.V1DeleteOptions()
    logging.warning(f'Deleting POD "{name}" from "{namespace}" namespace. ')
    api_response = core_v1.delete_namespaced_pod(name=name, namespace=namespace, body=delete_options)

    logging.info(api_response)


def cleanup(namespace):
    logging.info("Loading Kubernetes configuration")
    config.load_incluster_config()
    logging.debug("Initializing Kubernetes client")
    core_v1 = client.CoreV1Api()
    logging.info(f"Listing namespaced pods in namespace {namespace}. ")
    pod_list = core_v1.list_namespaced_pod(namespace)

    for pod in pod_list.items:
        logging.info(f"Inspecting pod {pod.metadata.name}. ")
        pod_phase = pod.status.phase.lower()
        pod_reason = pod.status.reason.lower() if pod.status.reason else ""
        pod_restart_policy = pod.spec.restart_policy.lower()

        if (
            pod_phase == POD_SUCCEEDED
            or (pod_phase == POD_FAILED and pod_restart_policy == POD_RESTART_POLICY_NEVER)
            or (pod_reason == POD_REASON_EVICTED)
        ):

            logging.info(
                f'Deleting pod "{pod.metadata.name}" phase "{pod_phase}" '
                f'and reason "{pod_reason}", restart policy "{pod_restart_policy}". '
            )

            try:
                delete_pod(pod.metadata.name, namespace)
            except ApiException as e:
                logging.error(f"can't remove POD: {e}. ")
                continue
        logging.info(f"No action taken on pod {pod.metadata.name}. ")


def main():
    parser = argparse.ArgumentParser(description="Clean up k8s pods in evicted/failed/succeeded states.")
    parser.add_argument("--namespace", dest="namespace", default="default", type=str, help="Namespace")
    args = parser.parse_args()
    cleanup(args.namespace)
