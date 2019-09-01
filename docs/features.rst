========
Features
========

Multiple Clusters
=================

Kubernetes Web View can access one or more clusters via different methods:

* In-cluster authorization via ServiceAccount: this is the default mode when deploying kube-web-view to a single cluster
* Static list of cluster API URLs passed via the ``--clusters`` CLI option, e.g. ``--clusters=myprodcluster=https://kube-prod.example.org;mytestcluster=https://kube-test.example.org``
* Clusters defined in kubeconfig file: kube-web-view will pick up all contexts defined in the kubeconfig file (``~/.kube/config`` or path given via ``--kubeconfig-path``). To only show some clusters, limit the kubeconfig contexts via the ``--kubeconfig-contexts`` command line option.
* Clusters defined in a cluster registry REST API: kube-web-view supports a custom REST API to discover clusters. Pass the URL via ``--cluster-registry-url`` and create a file with the OAuth2 Bearer token (``--cluster-registry-oauth2-bearer-token-path``). See the `example Cluster Registry REST API <https://codeberg.org/hjacobs/kube-web-view/src/branch/master/examples/cluster-registry>`_.

See also :ref:`multiple-clusters`.

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

Columns can be customized via the ``labelcols`` and ``customcols`` query parameters:

* ``labelcols`` is either a comma separated list of label names or "*" to show all labels
* ``customcols`` is a semicolon-separated list of Name=spec pairs, where "Name" is an arbitrary column name string and "spec" is a `JMESPath <http://jmespath.org/>`_ expression: e.g. ``Images=spec.containers[*].image`` would show the container images in the "Images" column. Note that the semicolon to separate multiple custom columns must be urlencoded as ``%3B``.
* ``hidecols`` is a comma separated list of column names to hide or "*" to hide all columns (label and custom columns will be added after the hide operation)

The ``limit`` query parameter can optionally limit the number of shown resources.

Searching
=========

Any resource type can be searched by name and/or label value across clusters and namespaces.
While Kubernetes Web View does not maintain its own search index, searches across clusters and resource types are done in parallel, so that results should be returned in a reasonable time.
Please note that the search feature might produce (heavy) load on the queried Kubernetes API servers.


Viewing Resources
=================

Object details are available via ``/clusters/{cluster}/{resource-type}/{name}`` for cluster resources
and ``/clusters/{cluster}/namespaces/{namespace}/{resource-type}/{name}`` for namespaced resources.
Object details are either rendered via HTML or can be viewed as their YAML source.
Resources can also be downloaded as YAML.

To make it easier to point colleagues to a specific portion of a resource spec, the YAML view supports linking and highlighting individual lines.
Just click on the respective line number.


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
