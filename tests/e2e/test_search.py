def test_search_form(session):
    response = session.get("/search")
    response.raise_for_status()
    search_results = response.html.find(".search-result")
    assert len(search_results) == 0
    assert "No results found for " not in response.text


def test_search_cluster(session):
    response = session.get("/search?q=local")
    response.raise_for_status()
    title = response.html.find(".search-result h3", first=True)
    assert title.text == "local (Cluster)"


def test_search_namespace(session):
    response = session.get("/search?q=default")
    response.raise_for_status()
    title = response.html.find(".search-result h3", first=True)
    assert title.text == "default (Namespace)"


def test_search_by_label(session):
    response = session.get("/search?q=application=kube-web-view")
    response.raise_for_status()
    title = response.html.find(".search-result h3", first=True)
    assert title.text == "kube-web-view (Deployment)"


def test_no_results_found(session):
    response = session.get("/search?q=stringwithnoresults")
    response.raise_for_status()
    search_results = response.html.find(".search-result")
    assert len(search_results) == 0
    p = response.html.find("main .content p", first=True)
    assert p.text == 'No results found for "stringwithnoresults".'


def test_search_non_standard_resource_type(session):
    response = session.get("/search?q=whatever&type=podsecuritypolicies")
    response.raise_for_status()
    # check that the type was added as checkbox
    labels = response.html.find("label.checkbox")
    assert "PodSecurityPolicy" in [label.text for label in labels]


def test_search_container_image_match_highlight(session):
    response = session.get("/search?q=hjacobs/wrong-container-image:&type=deployments")
    response.raise_for_status()
    match = response.html.find(".search-result .match", first=True)
    assert (
        '<span class="match"><em>hjacobs/wrong-container-image:</em>0.1</span>'
        == match.html
    )


def test_search_forbidden_namespace(session):
    response = session.get("/search?q=forbidden&type=deployments")
    response.raise_for_status()
    matches = list(response.html.find("main .search-result"))
    assert len(matches) == 0
