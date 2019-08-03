import pytest

from pykube import Pod
from pykube.query import Table

from kube_web.table import add_label_columns, filter_table, sort_table


@pytest.fixture
def single_pod_table():
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "Name"}, {"name": "Status"}],
            "rows": [{"cells": ["myname", "ImagePullBackOff"]}],
        },
    )
    return table


@pytest.fixture
def two_pod_table():
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "Name"}],
            "rows": [{"cells": ["pod-a"]}, {"cells": ["pod-b"]}],
        },
    )
    return table


def test_add_label_columns():
    table = Table(Pod, {"kind": "Table", "columnDefinitions": [], "rows": []})
    add_label_columns(table, "foo, bar")
    assert table.columns == [
        {"name": "Foo", "description": "foo label"},
        {"name": "Bar", "description": "bar label"},
    ]


def test_filter_table_wrong_column_name(single_pod_table):
    table = single_pod_table
    filter_table(table, "a=b")
    assert len(table.rows) == 0


def test_filter_table_no_match(single_pod_table):
    table = single_pod_table
    filter_table(table, "Name=b")
    assert len(table.rows) == 0


def test_filter_table_column_match(single_pod_table):
    table = single_pod_table
    filter_table(table, "Name=myname")
    assert len(table.rows) == 1


def test_filter_table_whitespace_ignore(single_pod_table):
    table = single_pod_table
    filter_table(table, " Name = myname ")
    assert len(table.rows) == 1


def test_filter_table_text_match(single_pod_table):
    table = single_pod_table
    filter_table(table, "myname")
    assert len(table.rows) == 1


def test_filter_table_text_match_case_insensitive(single_pod_table):
    table = single_pod_table
    filter_table(table, " MyName")
    assert len(table.rows) == 1


def test_filter_table_text_match_case_insensitive2(single_pod_table):
    table = single_pod_table
    filter_table(table, "backoff")
    assert len(table.rows) == 1


def test_filter_table_text_no_match(single_pod_table):
    table = single_pod_table
    filter_table(table, "othername")
    assert len(table.rows) == 0


def test_sort_table(two_pod_table):
    table = two_pod_table
    sort_table(table, "Name")
    assert table.rows[0]["cells"][0] == "pod-a"
    assert table.rows[1]["cells"][0] == "pod-b"


def test_sort_table_desc(two_pod_table):
    table = two_pod_table
    sort_table(table, "Name:desc")
    assert table.rows[0]["cells"][0] == "pod-b"
    assert table.rows[1]["cells"][0] == "pod-a"
