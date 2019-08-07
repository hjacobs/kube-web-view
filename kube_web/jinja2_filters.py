import colorsys
import datetime
import yaml as pyyaml

import pygments
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter


def pluralize(singular):
    if singular.endswith("s"):
        # Ingress -> Ingresses
        return singular + "es"
    elif singular.endswith("y"):
        # NetworkPolicy -> NetworkPolicies
        return singular[:-1] + "ies"
    else:
        return singular + "s"


def yaml(value):
    return pyyaml.dump(value, default_flow_style=False)


def highlight(value, linenos=False):

    if linenos:
        formatter = HtmlFormatter(
            lineanchors="line",
            anchorlinenos=True,
            linenos="table",
            linespans="yaml-line",
        )
    else:
        formatter = HtmlFormatter()

    return pygments.highlight(value, get_lexer_by_name("yaml"), formatter)


def age_color(date_time, days=7):
    """Return HTML color calculated by age of input time value.
    :param d: datetime value to base color calculation on
    :param days: upper limit for color calculation, in days
    :return: HTML color value string
    """

    if not date_time:
        return "auto"
    if isinstance(date_time, str):
        date_time = datetime.datetime.strptime(date_time, "%Y-%m-%dT%H:%M:%SZ")
    d = datetime.datetime.utcnow() - date_time
    # we consider the last minute equal
    d = max(0, d.total_seconds() - 60)
    v = max(0, 1.0 - d / (days * 24.0 * 3600))
    # dates older than days are color #363636 (rgb(54, 54, 54))
    r, g, b = colorsys.hsv_to_rgb(0.39, v, 0.21 + (v * 0.6))
    return (
        f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"
    )


def cpu(value):
    return "{:,.0f}m".format(value * 1000)


def memory(value, fmt):
    if fmt == "GiB":
        return "{:,.01f}".format(value / (1024 ** 3))
    elif fmt == "MiB":
        return "{:,.0f}".format(value / (1024 ** 2))
    else:
        return value
