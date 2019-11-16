import inspect
import re
from pyvis.network import Network
import networkx as nx

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# does not match to any symbol
REGEX_NEVER_MATCH = '(?!x)x'

NON_EXECUTABLE = "save|write|remove|delete"


def collect_ignored_functions():
    ignore_functions = set()
    if HAS_NUMPY:
        for func_name, func in inspect.getmembers(np.ndarray):
            ignore_functions.add(func_name)
    return ignore_functions


def get_module_root(obj):
    return obj.__class__.__module__.split('.')[0]


class IgnoreFunc:
    def __init__(self, ignore=''):
        self.ignore = re.compile(ignore, flags=re.IGNORECASE)
        self.ignored_functions = collect_ignored_functions()

    def __call__(self, obj, func_name):
        is_numpy = HAS_NUMPY and isinstance(obj, np.ndarray) and func_name in self.ignored_functions
        return self.ignore.search(func_name) or is_numpy


def to_pyvis(graph):
    """
    This method takes an exisitng Networkx graph and translates
    it to a PyVis graph format that can be accepted by the VisJs
    API in the Jinja2 template. This operation is done in place.

    Parameters
    ----------
    graph : nx.DiGraph
        NetworkX directed graph.

    Returns
    -------
    net : Network
        PyVis Network
    """
    edges = graph.edges(data='label')
    nodes = graph.nodes
    net = Network(height="960px", width="1280px", directed=True, layout=True)
    for (v, u, label) in edges:
        v_level = nodes[v]['level']
        u_level = nodes[u]['level']
        net.add_node(v, label=nodes[v]['label'], level=v_level, color='red' if v_level == 0 else None, title=nodes[v]['title'])
        net.add_node(u, label=nodes[u]['label'], level=u_level, title=nodes[u]['title'])
        net.add_edge(v, u, title=label, color='magenta' if u_level == v_level - 1 else 'blue')
    return net


def to_string(graph, source, prefix=''):
    if len(graph.adj[source]) == 0:
        yield f"{prefix} -> '{graph.nodes[source]['label']}'"
    else:
        for adj, attr in graph.adj[source].items():
            yield from to_string(graph, source=adj, prefix=f"{prefix}.{attr['label']}")
