.. _setup:

=====
Setup
=====

This section guides through the various options of setting up Kubernetes Web View in your environment.

* Do you want to use kube-web-view as a local development/ops tool? See :ref:`local-usage`
* Do you want to use it in a single cluster or access multiple clusters via kube-web-view? See :ref:`single-cluster` or :ref:`multiple-clusters`.
* How do you plan to secure your setup and authenticate users? See :ref:`access-control`.
* Do you want to customize behavior and look & feel for your organization? See :ref:`customization`.
* Please make sure to read the :ref:`security`.


.. _local-usage:

Local Usage
===========

Kubernetes Web View was primarily built for a (central) deployment, but you can run it locally with your existing Kubeconfig file (default location is ``~/.kube/config``).
This will automatically pick up all contexts defined in Kubeconfig, i.e. works with single or multiple clusters:

.. code-block:: bash

    docker run -it -p 8080:8080 -u $(id -u) -v $HOME/.kube:/.kube hjacobs/kube-web-view

Open http://localhost:8080/ in your browser to see the UI.

Note that Kubernetes Web View does not support all different proprietary authentication mechanisms (like EKS, GCP),
you can use "kubectl proxy" as a workaround:

.. code-block:: bash

    kubectl proxy --port=8001 &  # start proxy in background
    docker run -it --net=host -u $(id -u) hjacobs/kube-web-view --clusters=local=http://localhost:8001

If you are using Docker for Mac, this needs to be slightly different in order to navigate the VM/container inception:

.. code-block:: bash

    $ kubectl proxy --accept-hosts '.*' --port=8001 &
    $ docker run -it -p 8080:8080 hjacobs/kube-web-view --clusters=local=http://docker.for.mac.localhost:8001

Now direct your browser to http://localhost:8080


.. _single-cluster:

Single Cluster
==============

Deploying Kubernetes Web View to a single cluster is straightforward as it will use RBAC and in-cluster ServiceAccount to talk with the Kubernetes API server:

.. code-block:: bash

    kubectl apply -f deploy/

You can now use "kubectl port-forward service/kube-web-view 8080:80" to access the UI on http://localhost:8080/ or expose kube-web-view with a LB/Ingress. See :ref:`access-control`.


.. _multiple-clusters:

Multiple Clusters
=================

Kubernetes Web View can access multiple clusters via different methods:

* Static list of cluster API URLs passed via the ``--clusters`` CLI option, e.g. ``--clusters=myprodcluster=https://kube-prod.example.org;mytestcluster=https://kube-test.example.org``
* Clusters defined in kubeconfig file: kube-web-view will pick up all contexts defined in the kubeconfig file (``~/.kube/config`` or path given via ``--kubeconfig-path``). To only show some clusters, limit the kubeconfig contexts via the ``--kubeconfig-contexts`` command line option. This behavior is the same as for :ref:`local-usage`.
* Clusters defined in a cluster registry REST API: kube-web-view supports a custom REST API to discover clusters. Pass the URL via ``--cluster-registry-url`` and create a file with the OAuth2 Bearer token (``--cluster-registry-oauth2-bearer-token-path``). See the `example Cluster Registry REST API <https://codeberg.org/hjacobs/kube-web-view/src/branch/master/examples/cluster-registry>`_.

Kubernetes Web View will access the Kubernetes API differently, depending on the configuration:

* when using ``--clusters``: no authentication method (or token from ``--cluster-auth-token-path``, or session token if ``--cluster-auth-use-session-token`` is set)
* when using ``--kubeconfig-path``: try to use the authentication method defined in the Kubeconfig file (e.g. client certificate)
* when using ``--cluster-registry-url``: use the Cluster Registry Bearer token from ``--cluster-registry-oauth2-bearer-token-path``
* when using ``--cluster-auth-token-path``: load the access token from the given file and use it as "Bearer" token for all Kubernetes API calls --- this overwrites any of the above authentication methods
* when using ``--cluster-auth-use-session-token``: use the OAuth session token as "Bearer" token for the Kubernetes API --- this overwrites any other authentication method and only works when :ref:`oauth2` is enabled

You can also combine the ``--clusters`` option with ``kubectl proxy`` to access clusters which have an unsupported authentication method:

* start ``kubectl proxy --port=8001`` in a sidecar container
* run the kube-web-view container with the ``--clusters=http://localhost:8001`` argument

You can use ``--cluster-auth-token-path`` to dynamically refresh the Bearer access token in the background.
This is useful if you need to rotate the token regularly (e.g. every hour). Either run a sidecar process with a shared volume (e.g. "emptyDir") to write/refresh the token
or mount a Kubernetes secret into kube-web-view's container at the given path.


.. _access-control:

Access Control
==============

There are multiple options to secure your Kubernetes Web View deployment:

* Internal service without LoadBalancer/Ingress: this requires ``kubectl port-forward service/kube-web-view 8080:80`` to access the web UI. This is the easiest option to set up (no LB/Ingress/proxy/OAuth required), but inconvenient to use.
* Using a custom LB/proxy: you can expose the kube-web-view frontend through a custom proxy (e.g. nginx with ACLs, AWS ALB with authorization, etc). The setup highly depends on your environment and infrastructure.
* Using the built-in OAuth support: kube-web-view has support for the authorization grant OAuth redirect flow which works with common OAuth providers such as Google, GitHub, Cognito, and others. See :ref:`oauth2` on how to configure OAuth in Kubernetes Web View.

Please also read the :ref:`security`.
