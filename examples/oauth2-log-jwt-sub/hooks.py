"""
Example hook to parse a JWT access token and log the "sub" claim.

To be used with --oauth2-authorized-hook option

See also https://kube-web-view.readthedocs.io/en/latest/oauth2.html
"""
import base64
import json
import logging

CLAIM_NAME = "sub"


async def oauth2_authorized(data: dict, session):
    # note: you could also use "id_token" if your OAuth provider returns it
    token = data["access_token"]
    header, payload, signature = token.split(".")
    # we don't need to verify the signature as the token comes fresh from OAuth provider
    decoded = base64.b64decode(payload + "=" * ((4 - len(payload) % 4) % 4)).decode(
        "utf-8"
    )

    payload_data = json.loads(decoded)

    user = payload_data[CLAIM_NAME]
    logging.info(f"User {user} was logged in")
    # allow login
    return True
