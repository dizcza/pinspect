import inspect
import logging
import re

import networkx as nx
from pyvis.network import Network

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# does not match to any symbol
REGEX_NEVER_MATCH = '(?!x)x'

NON_EXECUTABLE = "save|write|remove|delete|duplicate"


def getmembers(obj_class):
    """
    Parameters
    ----------
    obj_class : type
        An object class.

    Returns
    -------
    member_names : set
        A set of method and attribute names of the `obj_class` type.

    """
    member_names = {func_name for func_name, func in inspect.getmembers(obj_class)}
    return member_names


def get_module_root(obj):
    return obj.__class__.__module__.split('.')[0]


class IgnoreFunc:
    def __init__(self, key, obj_class=()):
        """
        Parameters
        ----------
        key : str or list, optional
            A string or a list of strings to ignore `obj` attributes and methods from being accessed and executed.
            Apart from user-provided strings, all methods that contain one of the following key-words will be ignored:
            'save', 'write', 'remove', 'delete', 'duplicate'
            For the total list of ignored key-words, see `NON_EXECUTABLE` in `utils.py`.
        obj_class : list, optional
            A list of class types to ignore.
            Apart from user-provided class types, all numpy functions will not be executed.
        """
        self.ignore = re.compile(key, flags=re.IGNORECASE)
        self.ignored_functions = dict()
        try:
            import numpy as np
            self.ignored_functions[np.ndarray] = getmembers(np.ndarray)
            self.ignored_functions[np.ndarray].update(getmembers(np))
        except ImportError:
            pass
        if not isinstance(obj_class, (list, tuple, set)):
            obj_class = [obj_class]
        for class_type in obj_class:
            self.ignored_functions[class_type] = getmembers(class_type)

    def __call__(self, obj, attribute_name):
        """
        Check the `obj` for the attribute name `func_name`.

        Parameters
        ----------
        obj : object
            Object to take the attribute from.
        attribute_name : str
            `obj` attribute name.
        Returns
        -------
        bool
            Whether this attribute should be ignored or not.
        """
        for ignored_class, ignored_functions in self.ignored_functions.items():
            if isinstance(obj, ignored_class) and attribute_name in ignored_functions:
                return True
        return self.ignore.search(attribute_name)


def to_pyvis(graph, layout=True):
    """
    This method takes an exisitng Networkx graph and translates
    it to a PyVis graph format that can be accepted by the VisJs
    API in the Jinja2 template.

    Parameters
    ----------
    graph : nx.DiGraph
        NetworkX directed graph.
    layout : bool
        Use hierarchical layout if this is set.

    Returns
    -------
    net : Network
        PyVis Network
    """
    def add_node(node_id):
        attr = nodes[node_id]
        net.add_node(node_id, label=attr['label'], level=attr['level'], color=attr.get('color', None),
                     title=attr['title'])

    edges = graph.edges.data()
    nodes = graph.nodes
    net = Network(height="960px", width="1280px", directed=True, layout=layout)
    for v, u, edge_attr in edges:
        add_node(v)
        add_node(u)
        net.add_edge(v, u, title=edge_attr['label'], color=edge_attr['color'])
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


def check_edge(graph, edge_label):
    """
    Parameters
    ----------
    graph : nx.DiGraph
        A graph.
    edge_label : str
        Edge label.

    Returns
    -------
    int
        Counts how many edges have the property `label` that matches `edge_label`.

    """
    filtered = [triple for triple in graph.edges.data('label') if triple[2].startswith(edge_label)]
    for v, u, label in filtered:
        logging.info(f"{graph.nodes[v]['label']}.{label} -> {graph.nodes[u]['label']}")
    return len(filtered)
