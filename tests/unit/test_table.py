import os
import timeit

import pytest
from pykube import Pod
from pykube.query import Table

from kube_web.table import add_label_columns
from kube_web.table import filter_table
from kube_web.table import filter_table_by_predicate
from kube_web.table import merge_cluster_tables
from kube_web.table import remove_columns
from kube_web.table import sort_table


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
def single_pod_table_with_labels():
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "Name"}, {"name": "Status"}],
            "rows": [
                {
                    "cells": ["myname", "ImagePullBackOff"],
                    "object": {"metadata": {"labels": {"label1": "labelval1"}}},
                }
            ],
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
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [],
            "rows": [{"cells": [], "object": {"metadata": {}}}],
        },
    )
    add_label_columns(table, "foo, bar")
    assert table.columns == [
        {"name": "Foo", "description": "foo label", "label": "foo"},
        {"name": "Bar", "description": "bar label", "label": "bar"},
    ]


def test_add_label_columns_empty():
    table = Table(Pod, {"kind": "Table", "columnDefinitions": [], "rows": []})
    add_label_columns(table, ", ")
    assert table.columns == []


def test_add_label_columns_all():
    table = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [],
            "rows": [{"cells": [], "object": {"metadata": {}}}],
        },
    )
    add_label_columns(table, "*")
    assert table.columns == [{"name": "Labels", "description": "* label", "label": "*"}]


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


def test_filter_table_text_match_label(single_pod_table_with_labels):
    table = single_pod_table_with_labels
    filter_table(table, "labelval1")
    assert len(table.rows) == 0


def test_filter_table_text_match_label2(single_pod_table_with_labels):
    table = single_pod_table_with_labels
    filter_table(table, "labelval1", match_labels=True)
    assert len(table.rows) == 1


def test_filter_table_text_match_multi(single_pod_table):
    table = single_pod_table
    # letters "m" and "a" are in both cells
    filter_table(table, "m, a")
    assert len(table.rows) == 1


def test_filter_table_text_no_match_multi(single_pod_table):
    table = single_pod_table
    # "my" matches first column, but "xxx" does not match
    filter_table(table, "my, xxx")
    assert len(table.rows) == 0


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


def test_filter_table_by_predicate(two_pod_table):
    table = two_pod_table
    filter_table_by_predicate(table, lambda row: row["cells"][0] == "pod-a")
    assert len(table.rows) == 1


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


def test_remove_columns(two_pod_table):
    table = two_pod_table
    remove_columns(table, "Status")
    assert len(table.columns) == 1
    assert table.rows[0]["cells"] == ["pod-a"]


def test_remove_all_columns(two_pod_table):
    table = two_pod_table
    remove_columns(table, "*")
    assert len(table.columns) == 0
    assert table.rows[0]["cells"] == []


def test_merge_cluster_tables(single_pod_table, two_pod_table):
    table = merge_cluster_tables(single_pod_table, two_pod_table)
    assert len(table.rows) == 3
    assert len(table.obj["clusters"]) == 2


def test_merge_cluster_tables_new_columns():
    table1 = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "Name"}, {"name": "Status"}],
            "rows": [{"cells": ["myname", "ImagePullBackOff"]}],
            "clusters": ["c1"],
        },
    )
    table2 = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [
                {"name": "Name"},
                {"name": "FooCol"},
                {"name": "Status"},
            ],
            "rows": [{"cells": ["myname", "foo", "ImagePullBackOff"]}],
            "clusters": ["c1"],
        },
    )
    table = merge_cluster_tables(table1, table2)
    assert len(table.obj["clusters"]) == 2
    assert table.columns == [{"name": "Name"}, {"name": "Status"}, {"name": "FooCol"}]
    assert table.rows == [
        {"cells": ["myname", "ImagePullBackOff", None]},
        {"cells": ["myname", "ImagePullBackOff", "foo"]},
    ]


def test_merge_cluster_tables_completely_different():
    table1 = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "A"}],
            "rows": [{"cells": ["a"]}],
            "clusters": ["c1"],
        },
    )
    table2 = Table(
        Pod,
        {
            "kind": "Table",
            "columnDefinitions": [{"name": "B"}],
            "rows": [{"cells": ["b"]}],
            "clusters": ["c1"],
        },
    )
    table = merge_cluster_tables(table1, table2)
    assert len(table.obj["clusters"]) == 2
    assert table.columns == [{"name": "A"}, {"name": "B"}]
    assert table.rows == [{"cells": ["a", None]}, {"cells": [None, "b"]}]


@pytest.mark.skipif(
    os.getenv("PERF_TEST") is None,
    reason="Performance tests only run when PERF_TEST is set",
)
def test_add_label_columns_performance(capsys):
    def _add_label_cols():
        table = Table(
            Pod,
            {
                "kind": "Table",
                "columnDefinitions": [{"name": "A"}, {"name": "C"}, {"name": "E"}],
                "rows": [
                    {
                        "cells": ["a", "c", "e"],
                        "object": {"metadata": {"labels": {"foo": "bar"}}},
                    }
                ]
                * 100,
                "clusters": ["c1"],
            },
        )
        add_label_columns(table, "*")

    with capsys.disabled():
        print("add_label_columns", timeit.timeit(_add_label_cols, number=1000))


@pytest.mark.skipif(
    os.getenv("PERF_TEST") is None,
    reason="Performance tests only run when PERF_TEST is set",
)
def test_filter_table_performance(capsys):
    def _filter_table():
        table = Table(
            Pod,
            {
                "kind": "Table",
                "columnDefinitions": [{"name": "A"}, {"name": "C"}, {"name": "E"}],
                "rows": [{"cells": ["a", "c", "e"]}] * 100,
                "clusters": ["c1"],
            },
        )
        filter_table(table, "c")

    with capsys.disabled():
        print("filter_table", timeit.timeit(_filter_table, number=1000))


@pytest.mark.skipif(
    os.getenv("PERF_TEST") is None,
    reason="Performance tests only run when PERF_TEST is set",
)
def test_marge_cluster_tables_performance(capsys):
    def merge_tables():
        table1 = Table(
            Pod,
            {
                "kind": "Table",
                "columnDefinitions": [{"name": "A"}, {"name": "C"}, {"name": "E"}],
                "rows": [{"cells": ["a", "c", "e"]}] * 100,
                "clusters": ["c1"],
            },
        )
        table2 = Table(
            Pod,
            {
                "kind": "Table",
                "columnDefinitions": [{"name": "B"}, {"name": "D"}],
                "rows": [{"cells": ["b", "d"]}] * 100,
                "clusters": ["c1"],
            },
        )
        merge_cluster_tables(table1, table2)

    with capsys.disabled():
        print("merge_cluster_tables", timeit.timeit(merge_tables, number=1000))
