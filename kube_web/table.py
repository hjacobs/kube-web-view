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
    label_columns = list(l.strip() for l in label_columns_param.split(","))
    for i, label_column in enumerate(label_columns):
        if label_column == "*":
            name = "Labels"
        else:
            name = label_column.capitalize()
        table.columns.insert(
            i + 1, {"name": name, "description": f"{label_column} label"}
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
                contents = row["object"]["metadata"]["labels"].get(label, "")
            row["cells"].insert(i + 1, contents)


def filter_table(table, filter_param):
    if not filter_param:
        return

    key_value = {}
    key_value_neq = {}
    text_filters = []

    for part in filter_param.split(","):
        k, sep, v = part.partition("=")
        if not sep:
            text_filters.append(part.strip().lower())
        elif k.endswith("!"):
            key_value_neq[k[:-1].strip()] = v.strip()
        else:
            key_value[k.strip()] = v.strip()

    index_filter = {}
    index_filter_neq = {}
    for i, col in enumerate(table.columns):
        filter_value = key_value.get(col["name"])
        if filter_value is not None:
            index_filter[i] = filter_value

        filter_value = key_value_neq.get(col["name"])
        if filter_value is not None:
            index_filter_neq[i] = filter_value

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

            filter_value = index_filter_neq.get(j)
            is_match = filter_value is None or str(cell) != filter_value
            if not is_match:
                break

        if is_match:
            for text in text_filters:
                if text not in " ".join(str(cell).lower() for cell in row["cells"]):
                    is_match = False
                    break

        if not is_match:
            del table.rows[i]
