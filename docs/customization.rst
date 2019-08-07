=============
Customization
=============

Kubernetes Web View's behavior and appearance can be customized
for the needs of your organization.

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
``partials/aside-menu.html``
    Template for the left sidebar, customize this to add your own links.
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



Static Assets
=============

As you might want to add or change static assets (e.g. JS, CSS, images),
you can point Kubernetes Web View to a folder containing your custom assets.
Use the ``--static-assets-path`` command line option for this and either build a custom Docker image or mount your asset directory into the pod.


.. _Jinja2: https://palletsprojects.com/p/jinja/
