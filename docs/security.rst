=======================
Security Considerations
=======================

Kubernetes Web View exposes all Kubernetes object details via its web frontend.
There are a number of security precautions to make:

* Do not expose Kubernetes Web View to the public without **authorization** (e.g. OAuth2 redirect flow or some authorizing web proxy).
* The default **RBAC** role for kube-web-view (provided in the  ``deploy`` folder) provides **full read-only access** to the cluster --- modify it accordingly to limit the scope.
* Design and **understand your access control**: decide whether you use kube-web-view only locally (with personal credentials), have a central deployment (with service credentials) to multiple clusters, or deployed per cluster with limited access.
* Understand the security risks of exposing your cluster details to Kubernetes Web View users --- you should only **trust users** who you would also give full read-only access to the Kubernetes API.
* Check your Kubernetes objects for **potential sensitive information**, e.g. application developers might have used container environment variables (``env``) to contain passwords (instead of using secrets or other methods), mitigate accordingly!


Kubernetes Web View tries to have some sane defaults to prevent information leakage:

* Pod container logs are not shown by default as they might contain sensitive information (e.g. access logs, personal data, etc). You have to enable them via the  ``--show-container-logs`` command line flag.
* Contents of Kubernetes secrets are masked out (hidden) by default. If you are sure that you want to show secrets (e.g. because you only run kube-web-view on your local computer (``localhost``)), you can disable this feature via the ``--show-secrets`` command line flag.

Note that these are just additional features to prevent accidental security issues --- **you are responsible for securing Kubernetes Web View appropriately!**
