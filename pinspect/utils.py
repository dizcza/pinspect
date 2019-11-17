import inspect
import re
from pyvis.network import Network
import networkx as nx

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# does not match to any symbol
REGEX_NEVER_MATCH = '(?!x)x'

NON_EXECUTABLE = "save|write|remove|delete|duplicate"


def collect_ignored_functions(obj_class):
    function_names = {func_name for func_name, func in inspect.getmembers(obj_class)}
    return function_names


def get_module_root(obj):
    return obj.__class__.__module__.split('.')[0]


class IgnoreFunc:
    def __init__(self, key='', obj_class=()):
        if key == '':
            key = REGEX_NEVER_MATCH
        self.ignore = re.compile(key, flags=re.IGNORECASE)
        self.ignored_functions = dict()
        try:
            import numpy as np
            self.ignored_functions[np.ndarray] = collect_ignored_functions(np.ndarray)
            self.ignored_functions[np.ndarray].update(collect_ignored_functions(np))
        except ImportError:
            pass
        if not isinstance(obj_class, (list, tuple, set)):
            obj_class = [obj_class]
        for class_type in obj_class:
            self.ignored_functions[class_type] = collect_ignored_functions(class_type)

    def __call__(self, obj, func_name):
        """
        Check the `obj` for the attribute name `func_name`.

        Parameters
        ----------
        obj : object
            Object to take the attribute from.
        func_name : str
            `obj`'s attribute name.
        Returns
        -------
        bool
            Whether this attribute should be ignored or not.
        """
        for ignored_class, ignored_functions in self.ignored_functions.items():
            if isinstance(obj, ignored_class) and func_name in ignored_functions:
                return True
        return self.ignore.search(func_name)


def to_pyvis(graph):
    """
    This method takes an exisitng Networkx graph and translates
    it to a PyVis graph format that can be accepted by the VisJs
    API in the Jinja2 template.

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
    """
    Traverse the graph and yield its string representation.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph, obtained by `GraphBuilder`.
    source : int
        Source node id.
    prefix : str
        This prefix will be accumulated in a full call history during successive calls of `to_string()`.

    Returns
    -------
    generator
        Generator of string traversal of the graph.
    """
    if len(graph.adj[source]) == 0:
        yield f"{prefix} -> '{graph.nodes[source]['label']}'"
    else:
        for adj, attr in graph.adj[source].items():
            yield from to_string(graph, source=adj, prefix=f"{prefix}.{attr['label']}")
