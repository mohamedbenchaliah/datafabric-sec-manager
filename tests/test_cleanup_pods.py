from unittest import mock
from unittest.mock import MagicMock

import kubernetes

from sec_manager.pods_cleaner import cleanup, delete_pod


@mock.patch("kubernetes.client.CoreV1Api.delete_namespaced_pod")
def test_delete_pod(delete_namespaced_pod):
    delete_pod("dummy", "awesome-namespace")
    delete_namespaced_pod.assert_called_with(body=mock.ANY, name="dummy", namespace="awesome-namespace")


@mock.patch("sec_manager.pods_cleaner.delete_pod")
@mock.patch("kubernetes.client.CoreV1Api.list_namespaced_pod")
@mock.patch("kubernetes.config.load_incluster_config")
def test_cleanup_succeeded_pods(load_incluster_config, list_namespaced_pod, delete_pod):
    pod1 = MagicMock()
    pod1.metadata.name = "dummy"
    pod1.status.phase = "Succeeded"
    pod1.status.reason = None
    list_namespaced_pod().items = [pod1]
    cleanup("awesome-namespace")
    delete_pod.assert_called_with("dummy", "awesome-namespace")
    load_incluster_config.assert_called_once()


@mock.patch("sec_manager.pods_cleaner.delete_pod")
@mock.patch("kubernetes.client.CoreV1Api.list_namespaced_pod")
@mock.patch("kubernetes.config.load_incluster_config")
def test_no_cleanup_failed_pods_wo_restart_policy_never(load_incluster_config, list_namespaced_pod, delete_pod):
    pod1 = MagicMock()
    pod1.metadata.name = "dummy2"
    pod1.status.phase = "Failed"
    pod1.status.reason = None
    pod1.spec.restart_policy = "Always"
    list_namespaced_pod().items = [pod1]
    cleanup("awesome-namespace")
    delete_pod.assert_not_called()
    load_incluster_config.assert_called_once()


@mock.patch("sec_manager.pods_cleaner.delete_pod")
@mock.patch("kubernetes.client.CoreV1Api.list_namespaced_pod")
@mock.patch("kubernetes.config.load_incluster_config")
def test_cleanup_failed_pods_w_restart_policy_never(load_incluster_config, list_namespaced_pod, delete_pod):
    pod1 = MagicMock()
    pod1.metadata.name = "dummy3"
    pod1.status.phase = "Failed"
    pod1.status.reason = None
    pod1.spec.restart_policy = "Never"
    list_namespaced_pod().items = [pod1]
    cleanup("awesome-namespace")
    delete_pod.assert_called_with("dummy3", "awesome-namespace")
    load_incluster_config.assert_called_once()


@mock.patch("sec_manager.pods_cleaner.delete_pod")
@mock.patch("kubernetes.client.CoreV1Api.list_namespaced_pod")
@mock.patch("kubernetes.config.load_incluster_config")
def test_cleanup_evicted_pods(load_incluster_config, list_namespaced_pod, delete_pod):
    pod1 = MagicMock()
    pod1.metadata.name = "dummy4"
    pod1.status.phase = "Failed"
    pod1.status.reason = "Evicted"
    pod1.spec.restart_policy = "Never"
    list_namespaced_pod().items = [pod1]
    cleanup("awesome-namespace")
    delete_pod.assert_called_with("dummy4", "awesome-namespace")
    load_incluster_config.assert_called_once()


@mock.patch("sec_manager.pods_cleaner.delete_pod")
@mock.patch("kubernetes.client.CoreV1Api.list_namespaced_pod")
@mock.patch("kubernetes.config.load_incluster_config")
def test_cleanup_api_exception_continue(load_incluster_config, list_namespaced_pod, delete_pod):
    delete_pod.side_effect = kubernetes.client.rest.ApiException(status=0)
    pod1 = MagicMock()
    pod1.metadata.name = "dummy"
    pod1.status.phase = "Succeeded"
    pod1.status.reason = None
    list_namespaced_pod().items = [pod1]
    cleanup("awesome-namespace")
    load_incluster_config.assert_called_once()
