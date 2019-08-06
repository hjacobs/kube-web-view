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


.. _Jinja2: https://palletsprojects.com/p/jinja/
