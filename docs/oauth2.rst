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
