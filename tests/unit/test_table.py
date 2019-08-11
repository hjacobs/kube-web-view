import pytest

from pykube import Pod
from pykube.query import Table

from kube_web.table import (
    add_label_columns,
    filter_table,
    sort_table,
    merge_cluster_tables,
)


@pytest.fixture
def single_pod_table():
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "Name"}, {"name": "Status"}],
            "rows": [{"cells": ["myname", "ImagePullBackOff"]}],
            "clusters": ["c1"],
        },
    )
    return table


@pytest.fixture
def two_pod_table():
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "Name"}, {"name": "Status"}],
            "rows": [
                {"cells": ["pod-a", "Running"]},
                {"cells": ["pod-b", "Completed"]},
            ],
            "clusters": ["c2"],
        },
    )
    return table


def test_add_label_columns():
    table = Table(Pod, {"kind": "Table", "columnDefinitions": [], "rows": []})
    add_label_columns(table, "foo, bar")
    assert table.columns == [
        {"name": "Foo", "description": "foo label", "label": "foo"},
        {"name": "Bar", "description": "bar label", "label": "bar"},
    ]


def test_add_label_columns_empty():
    table = Table(Pod, {"kind": "Table", "columnDefinitions": [], "rows": []})
    add_label_columns(table, ", ")
    assert table.columns == []


def test_filter_table_wrong_column_name(single_pod_table):
    table = single_pod_table
    filter_table(table, "a=b")
    assert len(table.rows) == 0


def test_filter_table_no_match(single_pod_table):
    table = single_pod_table
    filter_table(table, "Name=b")
    assert len(table.rows) == 0


def test_filter_table_empty(single_pod_table):
    table = single_pod_table
    filter_table(table, "")
    assert len(table.rows) == 1


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


def test_filter_table_not_equal(two_pod_table):
    table = two_pod_table
    filter_table(table, "Name!=pod-a")
    assert len(table.rows) == 1
    assert table.rows[0]["cells"][0] == "pod-b"


def test_filter_table_not_equal_and(two_pod_table):
    table = two_pod_table
    filter_table(table, "Status!=Running,Status!=Completed")
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


def test_merge_cluster_tables(single_pod_table, two_pod_table):
    table = merge_cluster_tables(single_pod_table, two_pod_table)
    assert len(table.rows) == 3
    assert len(table.obj["clusters"]) == 2
