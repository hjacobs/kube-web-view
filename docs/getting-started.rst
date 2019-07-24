===============
Getting Started
===============

You can find example Kubernetes manifests for deployment in the deploy folder. You need a running Kubernetes cluster (version 1.10+) and ``kubectl`` correctly configured.
A local test cluster with Minikube_ or kind_ will also work.
It should be as simple as:

.. code-block:: bash

    $ git clone https://codeberg.org/hjacobs/kube-web-view
    $ kubectl apply -f kube-web-view/deploy

Afterwards you can open "kube-web-view" via kubectl port-forward (you might need to wait a bit for the pod to become ready):

.. code-block:: bash

    $ kubectl port-forward service/kube-web-view 8080:80

Now direct your browser to http://localhost:8080/

.. _Minikube: https://github.com/kubernetes/minikube
.. _kind: https://kind.sigs.k8s.io/


