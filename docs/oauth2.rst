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
