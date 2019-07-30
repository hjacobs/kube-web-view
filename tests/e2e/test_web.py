import requests


def test_generic_404_error(populated_cluster):
    url = populated_cluster["url"].rstrip("/")
    response = requests.get(f"{url}/this-page-does-not-exist")
    assert response.status_code == 404
    assert "Not Found" in response.text
    # check that our template is used
    assert "Kubernetes Web View" in response.text
