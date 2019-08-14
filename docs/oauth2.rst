.. _oauth2:

==============
OAuth2 Support
==============

Kubernetes Web View support OAuth2 for protecting its web frontend. Use the following environment variables to enable it:

``OAUTH2_AUTHORIZE_URL``
    OAuth 2 authorization endpoint URL, e.g. https://oauth2.example.org/authorize
``OAUTH2_ACCESS_TOKEN_URL``
    Token endpoint URL for the OAuth 2 Authorization Code Grant flow, e.g. https://oauth2.example.org/token
``OAUTH2_CLIENT_ID``
    OAuth 2 client ID
``OAUTH2_CLIENT_ID_FILE``
    Path to file containing the client ID. Use this instead of ``OAUTH2_CLIENT_ID`` to read the client ID dynamically from file.
``OAUTH2_CLIENT_SECRET``
    OAuth 2 client secret
``OAUTH2_CLIENT_SECRET_FILE``
    Path to file containing the client secret. Use this instead of ``OAUTH2_CLIENT_SECRET`` to read the client secret dynamically from file.
``SESSION_SECRET_KEY``
    Secret to encrypt the session cookie. Must be 32 bytes base64-encoded. Use ``cryptography.fernet.Fernet.generate_key()`` to generate such a key.

The OAuth2 login flow will (by default) just protect the web frontend, the configured credentials (in-cluster Service Account, Kubeconfig, or Cluster Registry) will be used to access the cluster(s).
This behavior can be changed and the session's OAuth2 access token can be used for cluster authentication instead of using configured credentials.
Enable this operation mode via ``--cluster-auth-use-session-token``.

The OAuth redirect flow will not do any extra authorization by default, i.e. everybody who can login with your OAuth provider can use Kubernetes Web View!
You can plug in a custom Python hook function (coroutine) via ``--oauth2-authorized-hook`` to validate the login or do any extra work (store extra info in the session, deny access, log user ID, etc).
Note that the hook needs to be a coroutine function with signature like ``async def authorized(data, session)``. The result should be boolean true if the login is successful, and false otherwise.
Examples of such hooks are provided in the `examples directory <https://codeberg.org/hjacobs/kube-web-view/src/branch/master/examples>`_. A minimal ``hooks.py`` would look like:

.. code-block:: python

    import logging

    async def oauth2_authorized(data: dict, session):
        access_token = data["access_token"]
        # TODO: do something with the access token, e.g. look up user info
        logging.info("New OAuth login!")
        # TODO: validate whether login is allowed or not
        return True  # allow all OAuth logins

This file would need to be in the Python search path, e.g. as ``hooks.py`` in the root ("/") of the Docker image. Pass the hook function as ``--oauth2-authorized-hook=hooks.oauth2_authorized`` to Kubernetes Web View.

Google OAuth Provider
=====================

This section explains how to use the Google OAuth 2.0 provider with Kubernetes Web View:

* follow the instructions on https://developers.google.com/identity/protocols/OAuth2 to obtain OAuth 2.0 credentials such as client ID and client secret
* use ``https://{my-kube-web-view-host}/oauth2/callback`` as one of the **Authorized redirect URIs** in the Google API Console
* use "https://accounts.google.com/o/oauth2/v2/auth?scope=email" for ``OAUTH2_AUTHORIZE_URL``
* use "https://oauth2.googleapis.com/token" for ``OAUTH2_ACCESS_TOKEN_URL``
* pass the obtained client ID in the ``OAUTH2_CLIENT_ID`` environment variable
* pass the obtained client secret in the ``OAUTH2_CLIENT_SECRET`` environment variable

GitHub OAuth Provider
=====================

How to use GitHub as the OAuth provider with Kubernetes Web View:

* create a new OAuth app in the GitHub UI
* use ``https://{my-kube-web-view-host}/oauth2/callback`` as the **Authorization callback URL** in the GitHub UI
* use "https://github.com/login/oauth/authorize" for ``OAUTH2_AUTHORIZE_URL``
* use "https://github.com/login/oauth/access_token" for the ``OAUTH2_ACCESS_TOKEN_URL``
* pass the obtained client ID in the ``OAUTH2_CLIENT_ID`` environment variable
* pass the obtained client secret in the ``OAUTH2_CLIENT_SECRET`` environment variable

Note that any GitHub user can now login to your deployment of Kubernetes Web View! You have to configure a ``--oauth2-authorized-hook`` function to validate the GitHub login and only allow certain usernames:

* copy ``hooks.py`` from ``examples/oauth2-validate-github-token/hooks.py`` (see `examples dir <https://codeberg.org/hjacobs/kube-web-view/src/branch/master/examples>`_) to a new folder
* customize the username in ``hooks.py`` to match your allowed GitHub user logins
* create a new ``Dockerfile`` in the same folder
* edit the ``Dockerfile`` to have two lines: 1) ``FROM hjacobs/kube-web-view:{version}`` (replace "{version}"!) as the first line, and 2) ``COPY hooks.py /`` to copy our OAuth validation function
* build the Docker image
* configure your kube-web-view deployment and add ``--oauth2-authorized-hook=hooks.oauth2_authorized`` as argument
* deploy kube-web-view with the new Docker image and CLI option
