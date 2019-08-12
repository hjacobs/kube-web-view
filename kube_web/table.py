import collections
from functools import partial


def _creation_timestamp(row):
    return row["object"]["metadata"]["creationTimestamp"]


def _column(row, column_index: int):
    return (row["cells"][column_index], row["cells"][0])


def sort_table(table, sort_param):
    if not sort_param:
        return
    parts = sort_param.split(":")
    sort = parts[0]
    reverse = len(parts) > 1 and parts[1] == "desc"
    if sort == "Created":
        key = _creation_timestamp
    elif sort == "Age":
        key = _creation_timestamp
        reverse = not reverse
    else:
        column_index = 0
        for i, col in enumerate(table.columns):
            if col["name"] == sort:
                column_index = i
                break
        key = partial(_column, column_index=column_index)
    table.rows.sort(key=key, reverse=reverse)


def add_label_columns(table, label_columns_param):
    if not label_columns_param:
        return
    label_columns = list(
        filter(None, [l.strip() for l in label_columns_param.split(",")])
    )
    for i, label_column in enumerate(label_columns):
        if label_column == "*":
            name = "Labels"
        else:
            name = label_column.capitalize()
        table.columns.insert(
            i + 1,
            {
                "name": name,
                "description": f"{label_column} label",
                "label": label_column,
            },
        )
    for row in table.rows:
        for i, label in enumerate(label_columns):
            if label == "*":
                contents = ",".join(
                    f"{k}={v}"
                    for k, v in sorted(
                        row["object"]["metadata"].get("labels", {}).items()
                    )
                )
            else:
                contents = row["object"]["metadata"].get("labels", {}).get(label, "")
            row["cells"].insert(i + 1, contents)


def filter_table(table, filter_param):
    if not filter_param:
        return

    key_value = {}
    key_value_neq = collections.defaultdict(set)
    text_filters = []

    for part in filter_param.split(","):
        k, sep, v = part.partition("=")
        if not sep:
            text_filters.append(part.strip().lower())
        elif k.endswith("!"):
            key_value_neq[k[:-1].strip()].add(v.strip())
        else:
            key_value[k.strip()] = v.strip()

    index_filter = {}
    index_filter_neq = {}
    for i, col in enumerate(table.columns):
        filter_value = key_value.get(col["name"])
        if filter_value is not None:
            index_filter[i] = filter_value

        filter_values = key_value_neq.get(col["name"])
        if filter_values is not None:
            index_filter_neq[i] = filter_values

    if len(key_value) != len(index_filter):
        # filter was defined for a column which does not exist
        table.rows[:] = []
        return

    if len(key_value_neq) != len(index_filter_neq):
        # filter was defined for a column which does not exist
        table.rows[:] = []
        return

    for i, row in reversed(list(enumerate(table.rows))):
        is_match = False
        for j, cell in enumerate(row["cells"]):
            filter_value = index_filter.get(j)
            is_match = filter_value is None or str(cell) == filter_value
            if not is_match:
                break

            filter_values = index_filter_neq.get(j)
            is_match = not filter_values or str(cell) not in filter_values
            if not is_match:
                break

        if is_match:
            for text in text_filters:
                if text not in " ".join(str(cell).lower() for cell in row["cells"]):
                    is_match = False
                    break

        if not is_match:
            del table.rows[i]


def merge_cluster_tables(t1, t2):
    """Merge two tables with same column from different clusters"""
    column_names1 = list([col["name"] for col in t1.columns])
    column_names2 = list([col["name"] for col in t2.columns])
    if column_names1 == column_names2:
        t1.rows.extend(t2.rows)
        t1.obj["clusters"].extend(t2.obj["clusters"])
        return t1
    else:
        added = 0
        for column in t2.columns:
            if column["name"] not in column_names1:
                t1.columns.append(column)
                added += 1
        column_indicies = {}
        for i, column in enumerate(t1.columns):
            column_indicies[column["name"]] = i
        for row in t1.rows:
            for i in range(added):
                row["cells"].append(None)
        for row in t2.rows:
            new_row_cells = [None] * len(t1.columns)
            for name, cell in zip(column_names2, row["cells"]):
                idx = column_indicies[name]
                new_row_cells[idx] = cell
            row["cells"] = new_row_cells
            t1.rows.append(row)

        t1.obj["clusters"].extend(t2.obj["clusters"])
        return t1
