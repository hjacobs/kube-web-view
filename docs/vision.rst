.. _vision:

==============
Vision & Goals
==============

    *"kubectl for the web!"*

Kubernetes Web View's goal is to provide a no-frills HTML frontend for listing and inspecting K8s objects in troubleshooting and incident response scenarios.

The main audience of Kubernetes Web View is experienced "power" users, on-call/SREs, and cluster operators.
Understanding Kubernetes concepts and resources is expected.

The focus on troubleshooting and "kubectl on the web" led to the following design principles and goals:

* enable all (read-only) operations where people commonly use ``kubectl`` as their tool of choice
* all URLs should represent the full view state (permalinks) in order to make them shareable among colleagues and facilitate deep-linking from other tools
* all Kubernetes objects should be supported to be able to troubleshoot any kind of problem
* resource lists should be easily downloadable for further processing (spreadsheet, CLI tools like ``grep``) and storage (e.g. for postmortems)
* selecting resources by label (similar to ``kubectl get .. -l``) should be supported
* composing views of different resource types should be possible (similar to ``kubectl get all``) to provide a common operational picture among colleagues (e.g. during incident response)
* adding custom "smart" deep links to other tools such as monitoring dashboards, logging providers, application registries, etc should be possible to facilitate troubleshooting and incident response
* keep the frontend as simple as possible (pure HTML) to avoid accidental problems, e.g. unresponsive JavaScript
* support multiple clusters to streamline discovery in on-call situations (only one entry URL to remember)
* facilitate ad-hoc analysis where possible (e.g. with download links for resources across clusters/namespaces)
* provide additional deep-linking and highlighting, e.g. to point colleagues to a certain part of a resource spec (line in YAML)
* allow customization for org-specific optimizations: e.g. custom view templates for CRDs, custom table views, custom CSS formatting
* provide means to continue investigation on the command line (e.g. by showing full ``kubectl`` command lines to copy)

Out-of-scope (non-goals) for Kubernetes Web View are:

* abstracting Kubernetes objects
* application management (e.g. managing deployments, Helm Charts, etc)
* write operations (this should be done via safe CI/CD tooling and/or GitOps)
* fancy UI (JavaScript, theming, etc)
* visualization (check out `kube-ops-view <https://github.com/hjacobs/kube-ops-view>`_)
* cost analysis (check out `kube-resource-report <https://github.com/hjacobs/kube-resource-report/>`_)
