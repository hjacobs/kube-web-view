# rolebindings cannot be listed
LINKS_TO_IGNORE = [
    "/clusters/local/clusterrolebindings",
    "/clusters/local/clusterroles",
    "/clusters/local/componentstatuses",
    "/clusters/local/namespaces/default/rolebindings",
    "/clusters/local/namespaces/default/roles",
]


def check_links(response, session, ignore=None):
    for link in response.html.links:
        if link.startswith("/") and link not in LINKS_TO_IGNORE:
            if ignore and link in ignore:
                continue
            r = session.get(link)
            r.raise_for_status()
