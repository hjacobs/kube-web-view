def test_search_namespace(session):
    response = session.get("/search?q=default")
    response.raise_for_status()
    title = response.html.find(".search-result h3", first=True)
    assert title.text == "default (Namespace)"
