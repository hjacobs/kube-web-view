def parse_selector(param: str):
    if not param:
        return None
    selector = {}
    conditions = param.split(",")
    for condition in conditions:
        key, _, val = condition.partition("=")
        key = key.strip()
        val = val.strip()
        if key.endswith("!"):
            if key not in selector:
                selector[key] = []
            selector[key].append(val)
        else:
            selector[key] = val
    return selector


def selector_matches(selector: dict, labels: dict):
    if not selector:
        return True
    for key, val in selector.items():
        if key.endswith("!"):
            if labels.get(key.rstrip("!")) in val:
                return False
        else:
            if labels.get(key) != val:
                return False
    return True
