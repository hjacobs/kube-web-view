import importlib
import logging
import pkgutil
from functools import reduce
from itertools import groupby
from pathlib import Path

import jsonschema
import yaml
from box import Box


def prepare_object_links(object_link_config):
    if not object_link_config:
        return None

    logging.debug(f'object link config: {object_link_config}')

    config = yaml.safe_load(object_link_config)

    schema = yaml.safe_load(pkgutil.get_data(__package__, 'object_link_schema.yaml'))
    # use https://www.jsonschemavalidator.net/ to troubleshoot
    # logging.info(json.dumps(schema, indent=2))
    jsonschema.validate(config, schema)

    def prepare(link):
        file = link.get('file')
        if file:
            spec = importlib.util.spec_from_file_location(Path(file).stem, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            link['function'] = eval(f"module.{link['function']}", {'module': module})
        else:
            if "icon" not in link:
                link["icon"] = "external-link-alt"
            if "title" not in link:
                link["title"] = "External link for object {metadata.name}"
        return link

    return {
        'groupOrder': {g: i for i, g in enumerate(config.get('groups', ['']))},
        'links': [prepare(l) for l in config.get('links', [])],
    }


def set_source(links):
    for link in links:
        source = link.get('source', {}) or {}
        source['group'] = source.get('group', '') or ''
        source['name'] = source.get('name', '') or ''
        link['source'] = source
    return links


def source_order(order, link):
    source = link['source']
    return order[source['group']], source['name']


def render_source(links):
    f = links[0]['source']
    result = {
        'name': f"{f['group']} {f['name']}".strip()
    }

    href = [l['source']['href'] for l in links if l['source'].get('href')]
    if href:
        result['href'] = href[0]

    return result, links


def render_group(links):
    by_name = [list(l) for _, l in groupby(links, lambda l: l['source']['name'])]

    if len(by_name) == 1:
        by_name[0][0]['source']['name'] = ''

    return [render_source(l) for l in by_name]


def render_object_links(object_link_config, cluster, resource):
    if not object_link_config:
        return {}

    box = Box(resource.obj)
    args = {
        "cluster": cluster,
        "kind": box.kind,
        "metadata": box.metadata,
        "spec": box.spec,
    }

    links = reduce(list.__add__, [render_object_link(l, cluster, box, args) for l in object_link_config['links']], [])

    order = object_link_config['groupOrder']
    links = sorted(set_source(links), key=lambda l: source_order(order, l))

    return reduce(list.__add__, [render_group(list(l)) for _, l in groupby(links, lambda l: l['source']['group'])], [])


def render(o, args):
    if isinstance(o, dict):
        return {k: render(v, args) for k, v in o.items()}
    return eval("f'''" + o + "'''", args)


def render_object_link(link, cluster, resource, args):
    if 'function' in link:
        if 'args' in link:
            args.update(link['args'])
        links = link['function'](**args)

        if not isinstance(links, list):
            links = [links]
        return links

    if 'kinds' in link and resource.metadata.kind not in link['kinds']:
        return []

    try:
        return [render(link, args)]
    except KeyError:
        # skip a link that is missing a required key
        return []
