"""
Example hook to validate GitHub user login.

To be used with --oauth2-authorized-hook option
"""
import aiohttp
import logging


# list of authorized GitHub usernames
AUTHORIZED_USERS = frozenset(["hjacobs"])


async def oauth2_authorized(data: dict, session):
    token = data["access_token"]
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://api.github.com/user", headers={"Authorization": f"token {token}"}
        ) as resp:
            user_info = await resp.json()
    login = user_info["login"]
    logging.info(f"GitHub login is {login}")
    if login not in AUTHORIZED_USERS:
        # not authorized to access this app!
        return False
    return True
