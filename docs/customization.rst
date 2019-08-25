=============
Customization
=============

Kubernetes Web View's behavior and appearance can be customized
for the needs of your organization:

* resource type links shown in the :ref:`sidebar` can be customized to add CRDs, or to optimize for frequent access
* default :ref:`label-columns` can be defined to show values of standardized object labels (e.g. "app", "version", etc)
* :ref:`external-links` can be added to link objects to monitoring tools, internal application registries, custom UIs, etc
* the :ref:`customize-search` can be customized to search in CRDs, or to cover frequent search cases
* setting :ref:`preferred-api-versions` allows forcing the use of specific/newer Kubernetes API versions
* :ref:`html-templates` can be customized to match your branding, to add static links, and to inject custom JS/CSS
* :ref:`static-assets` can be included to add images, JS, or CSS files


.. _sidebar:

Sidebar
=======

The resource types linked in the left sidebar can be customized, e.g. to include CRDs or to remove resource types which are not frequently accessed.

Example command line argument to show the "StackSet" CRD in the "Controllers" section and to add secrets to "Pod Management":

.. code-block:: bash

    --sidebar-resource-types=Controllers=stacksets,deployments,cronjobs;Pod Management=ingresses,services,pods,secrets

You can use :ref:`html-templates` for further customization of the sidebar (e.g. to add non-resource links).


.. _label-columns:

Label & Custom Columns
======================

Most organizations have a standard set of labels for Kubernetes resources, e.g. all pods might have "app" and "version" labels.
You can instruct Kubernetes Web View to show these labels as columns for the respective resource types via the ``--default-label-columns`` command line option.

Example command line argument to show the "application" and "version" labels for pods and the "team" label for deployments:

.. code-block:: bash

    --default-label-columns=pods=application,version;deployments=team

Note that the label names are separated by comma (",") whereas multiple different entries for different resource types are separated by semicolon (";").

Users of the web UI can remove the pre-configured label columns by passing a single comma as the ``labelcols`` query parameter: ``/clusters/../namespaces/_all/pods?labelcols=,``.

You can hide existing columns via the ``--default-hidden-columns`` command line option, e.g. to remove the "Nominated Node" and "Readiness Gates" columns from pod tables:

.. code-block:: bash

    --default-hidden-columns=pods=Nominated Node,Readiness Gates

Arbitrary custom columns can be defined with `JMESPath <http://jmespath.org>`_ expressions, e.g. add a column "Images" for pods and the column "Strategy" for deployments:

.. code-block:: bash

    --default-custom-columns=pods=Images=spec.containers[*].image;;deployments=Strategy=spec.strategy

Multiple column definitions are separated by a single semicolon (";") whereas multiple different entries for different resource types are separated by two semicolons (";;").
Please be aware that custom columns require one additional Kubernetes API call per listing.


.. _external-links:

External Links
==============

You can configure external links per resource type or based on certain labels with these two command line options:

``--object-links``
    Define URL templates per resource type (e.g. to link all pods to a monitoring dashboard per pod)
``--label-links``
    Define URL templates per label, e.g. to link to an application registry for the "app" label, team overview for a "team" label, etc

The URL templates are Python string format strings and receive the following variables for replacement:

``{cluster}``
    The cluster name.
``{namespace}``
    The namespace name of the object.
``{name}``
    The object name.
``{label}``
    Only for label links: the label name.
``{label_value}``
    Only for label links: the label value.

Example command line argument to add links to a monitoring dashboard per pod:

.. code-block:: bash

    --object-links=pods=https://mymonitoringsystem/pod-dashboard?cluster={cluster};namespace={namespace};name={name}

Example command line argument to link resources with an "application" label to `Kubernetes Resource Report <https://github.com/hjacobs/kube-resource-report/>`_:

.. code-block:: bash

    --label-links=application=https://myresourcereport/application-{label_value}.html

.. _customize-search:

Search
======

The default search resource types can be customized, e.g. to include Custom Resource Definitions (CRDs) or to optimize for frequent search patterns.
Pass comma-separated lists of resource types (plural name) to the following two command line options:

``--search-default-resource-types``
    Set the resource types to search by default (when using the navbar search box). Must be a comma-separated list of resource types, e.g. "deployments,pods".
``--search-offered-resource-types``
    Customize the list of resource types shown on the search page (``/search``). Must be a comma-separated list of resource types, e.g. "deployments,pods,nodes".

Note that all resource types can be searched by using a deep-link, i.e. these options will only restrict what is shown in the HTML UI, but they will not prohibit searching for other resource types.

.. _preferred-api-versions:

Preferred API Versions
======================

You might want to change the default preferred API version returned by the Kubernetes API server.
This is useful to force using a later/newer API version for some resources, e.g. the Kubernetes HorizontalPodAutoscaler has a different spec for later versions.

Here the example CLI option to force using new API versions for Deployment and HPA (the default is ``autoscaling/v1`` as of Kubernetes 1.14):

.. code-block:: bash

    --preferred-api-versions=horizontalpodautoscalers=autoscaling/v2beta2;deployments=apps/v1


.. _html-templates:

HTML Templates
==============

Custom Jinja2_ HTML templates can override any of the default templates.
Mount your custom templates into kube-web-view's pod and point the ``--templates-path`` to it.

Here some of the common templates you might want to customize:

``base.html``
    The main HTML layout (contains ``<head>`` and ``<body>`` tags).
``partials/extrahead.html``
    Optional extra content for the ``<head>`` HTML part. Use this template to add any custom JS/CSS.
``partials/navbar.html``
    The top navigation bar.
``partials/sidebar.html``
    Template for the left sidebar, customize this to add your own links. Note that you can change the list of resource types without touching HTML via ``--sidebar-resource-types``, see :ref:`the sidebar section <sidebar>`.
``partials/footer.html``
    Footer element at the end of the HTML ``<body>``.

You can find all the standard templates in the official git repo: https://codeberg.org/hjacobs/kube-web-view/src/branch/master/kube_web/templates

You can build your own Docker image containing the templates or you can use a volume of type ``emptyDir`` and some InitContainer to inject your templates.
Example pod spec with a custom footer:

.. code-block:: yaml


    spec:
      initContainers:
      - name: generate-templates
        image: busybox
        command: ["sh", "-c", "mkdir /templates/partials && echo '<footer class=\"footer\">YOUR CUSTOM CONTENT HERE</footer>' > /templates/partials/footer.html"]
        volumeMounts:
        - mountPath: /templates
          name: templates

      containers:
      - name: kube-web-view
        # see https://codeberg.org/hjacobs/kube-web-view/releases
        image: hjacobs/kube-web-view:latest
        args:
        - --port=8080
        - --templates-path=/templates
        ports:
        - containerPort: 8080
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
        volumeMounts:
        - mountPath: /templates
          name: templates
          readOnly: true
        resources:
          limits:
            memory: 100Mi
          requests:
            cpu: 5m
            memory: 100Mi
        securityContext:
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
      volumes:
      - name: templates
        emptyDir:
          sizeLimit: 50Mi


.. _static-assets:

Static Assets
=============

As you might want to add or change static assets (e.g. JS, CSS, images),
you can point Kubernetes Web View to a folder containing your custom assets.
Use the ``--static-assets-path`` command line option for this and either build a custom Docker image or mount your asset directory into the pod.


.. _Jinja2: https://palletsprojects.com/p/jinja/
