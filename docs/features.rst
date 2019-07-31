========
Features
========

Multiple Clusters
=================

Kubernetes Web View can access one or more clusters via different methods:

* In-cluster authorization via ServiceAccount: this is the default mode when deploying kube-web-view to a single cluster
* Clusters defined in kubeconfig file: kube-web-view will pick up all contexts defined in the kubeconfig file (``~/.kube/config`` or path given via ``--kubeconfig-path``). To only show some clusters, limit the kubeconfig contexts via the ``--kubeconfig-contexts`` command line option.
* Clusters defined in a cluster registry REST API: kube-web-view supports a custom REST API to discover clusters. Pass the URL via ``--cluster-registry-url`` and create a file with the OAuth2 Bearer token (``--cluster-registry-oauth2-bearer-token-path``).

Listing Resources
=================

Kubernetes Web View can list all Kubernetes resource types:

* non-namespaced cluster resources under ``/clusters/{cluster}/{plural}``
* namespaced resources under ``/clusters/{cluster}/namespaces/{namespace}/{plural}``

Multiple resource types can be listed on the same page by using their comma-separated plural resource names, e.g. to list deployments and ingresses on the same page: ``/clusters/{cluster}/namespaces/{namespace}/deployments,ingresses``.
Try out the `live demo with deployments and ingresses on the same page <https://kube-web-view.demo.j-serv.de/clusters/local/namespaces/default/deployments,ingresses>`_.

To list resources across all namespaces, use ``_all`` for the namespace name in the URL.

Resources can be listed across all clusters by using ``_all`` for the cluster name in the URL.

Resources can be filtered by label: use the ``selector`` query parameter with label key=value pairs.

To facilitate processing in spreadsheets or command line tools (``grep``, ``awk``, etc), all resource listings can be downloaded as tab-separated-values (TSV). Just append ``download=tsv`` to the URL.

Viewing Resources
=================

Object details are available via ``/clusters/{cluster}/{resource-type}/{name}`` for cluster resources
and ``/clusters/{cluster}/namespaces/{namespace}/{resource-type}/{name}`` for namespaced resources.
Object details are either rendered via HTML or can be viewed as their YAML source.

Container Logs
==============

Kubernetes Web View supports rendering pod container logs for individual pods and any resource spec with ``matchLabels``, i.e. Deployments, ReplicaSets, DaemonSets, and StatefulSets.
Just use the "Logs" tab or append ``/logs`` to the resource URL.

Note that container logs are disabled by default for security reasons, enable them via ``--show-container-logs``.

Custom Resource Definitions (CRDs)
==================================

Kubernetes Web View automatically works for your CRDs. The list (table) view will render similar to the output of ``kubectl get ..``,
i.e. you can customize displayed table columns by modifying the ``additionalPrinterColumns`` section of your CRD section.
See the `official Kubernetes docs on additional printer columns <https://kubernetes.io/docs/tasks/access-kubernetes-api/custom-resources/custom-resource-definitions/#additional-printer-columns>`_ for details.

OAuth2
======

The web frontend can be secured via the builtin OAuth2 Authorization Grant flow support, see the :ref:`oauth2` section for details.
