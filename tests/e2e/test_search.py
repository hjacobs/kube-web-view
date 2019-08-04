def test_search_form(session):
    response = session.get("/search")
    response.raise_for_status()
    search_results = response.html.find(".search-result")
    assert len(search_results) == 0
    assert 'No results found for ' not in response.text


def test_search_namespace(session):
    response = session.get("/search?q=default")
    response.raise_for_status()
    title = response.html.find(".search-result h3", first=True)
    assert title.text == "default (Namespace)"


def test_no_results_found(session):
    response = session.get("/search?q=stringwithnoresults")
    response.raise_for_status()
    search_results = response.html.find(".search-result")
    assert len(search_results) == 0
    p = response.html.find(".main .content p", first=True)
    assert p.text == 'No results found for "stringwithnoresults".'
