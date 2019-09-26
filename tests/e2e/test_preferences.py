def test_preferences(session):
    response = session.get("/preferences")
    response.raise_for_status()
    select = response.html.find("main select", first=True)
    options = [o.text for o in select.find("option")]
    assert options == ["darkly", "default", "flatly", "slate", "superhero"]
