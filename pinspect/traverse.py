import contextlib
import inspect
import re
from collections import namedtuple
from pprint import pformat

import networkx as nx
from tqdm import tqdm

from pinspect.utils import get_module_root, IgnoreFunc, REGEX_NEVER_MATCH, NON_EXECUTABLE, to_pyvis, to_string

Match = namedtuple("Match", ("attributes", "classes"))


class DiGraphAcyclic(nx.DiGraph):
    def add_edge(self, u_of_edge, v_obj, **attr):
        v_of_edge = id(v_obj)
        self.add_node(v_obj, level=self.nodes[u_of_edge]['level'] + 1)
        if nx.has_path(self, v_of_edge, u_of_edge):
            # makes cycle
            return False
        super().add_edge(u_of_edge, v_of_edge, **attr)
        return True

    def add_node(self, obj, **attr):
        if id(obj) in self.nodes:
            return False
        label = obj.__class__.__name__
        if isinstance(obj, (set, list, tuple, dict)):
            label = f"{label} of size {len(obj)}"
        title = pformat(obj, depth=1, compact=True)
        title = title.splitlines()
        title_short = title[0]
        if len(title) > 1:
            title_short = f"{title_short} ..., {title[-1]}"
        title_short = title_short.strip('<>')
        super().add_node(id(obj), label=label, title=title_short, **attr)
        return True


class GraphBuilder:
    def __init__(self, key, module, ignore_key='', ignore_class=()):
        if key == '':
            key = REGEX_NEVER_MATCH
        self.key = re.compile(key, flags=re.IGNORECASE)
        self.module = module
        nonexec = NON_EXECUTABLE
        if ignore_key:
            nonexec = f"{nonexec}|{ignore_key}"
        self.nonexec = re.compile(nonexec)
        self.ignore_attribute = IgnoreFunc(key=ignore_key, obj_class=ignore_class)
        self.tried_functions = set()
        self.tried_classes = set()
        self.max_depth = 10
        self.debug = False
        self.graph = DiGraphAcyclic()

    def traverse(self, obj, parent_edge=None, level=0):
        if level >= self.max_depth:
            return

        if parent_edge is not None:
            parent, edge_name = parent_edge
            if not self.graph.add_edge(id(parent), obj, label=edge_name):
                # makes a cycle
                return
            if isinstance(obj, (bool, int, str, float, type)):
                # ignore builtin types
                return

        if isinstance(obj, dict):
            for key, value in obj.items():
                self.traverse(value, parent_edge=(obj, f"['{key}']"), level=level + 1)
            return

        if isinstance(obj, (set, list, tuple)):
            if len(obj) > 0:
                element = next(iter(obj))
                if parent_edge is not None:
                    parent, edge_name = parent_edge
                    self.graph.remove_node(id(obj))
                    self.traverse(element, parent_edge=(parent, f"{edge_name}[0]"), level=level + 1)
                else:
                    self.traverse(element, parent_edge=(obj, "[0]"), level=level + 1)
            return

        if get_module_root(obj) != self.module:
            # we're interested only in functions of the given module
            return

        if obj.__class__ in self.tried_classes:
            return
        self.tried_classes.add(obj.__class__)

        if self.debug:
            print(f"{' ' * level}Inspecting {obj.__class__.__name__} (level={level}): {obj}")

        for attr_name in tqdm(dir(obj), desc=f"Inspecting '{obj.__class__.__name__}'",
                              disable=level > 0):
            if attr_name.startswith('__'):
                continue
            if self.ignore_attribute(obj, attr_name):
                continue
            try:
                attr = getattr(obj, attr_name)
            except ValueError:
                continue
            full_name = f"{obj.__class__.__name__}.{attr_name}"
            if callable(attr) and full_name not in self.tried_functions and not self.nonexec.search(attr_name):
                try:
                    if self.debug:
                        print(f"{' ' * (level + 1)}Executing {obj.__class__.__name__}.{attr_name}()")
                    with contextlib.redirect_stdout(None):
                        res = attr()
                except Exception as err:
                    # create a new exception to make sure the id is unique
                    err = err.__class__(str(err))
                    self.graph.add_edge(id(obj), err, label=f"{attr_name}()")
                else:
                    self.tried_functions.add(full_name)
                    self.traverse(res, parent_edge=(obj, f"{attr_name}()"), level=level + 1)
            elif not inspect.ismethod(attr):
                self.traverse(attr, parent_edge=(obj, attr_name), level=level + 1)

    def strip(self, types_only=False):
        graph = self.graph.reverse(copy=False)
        graph_stripped = nx.DiGraph()
        for node_from in nx.topological_sort(graph):
            if self.key.search(graph.nodes[node_from].get('label', '')):
                include_parents = True
            else:
                include_parents = graph.nodes[node_from].get('include', False)
            for node_to, edge_attr in graph.adj[node_from].items():
                if include_parents or (not types_only and self.key.search(edge_attr['label'])):
                    graph.nodes[node_to]['include'] = True
                    graph_stripped.add_node(node_to, **graph.nodes[node_to])
                    graph_stripped.add_node(node_from, **graph.nodes[node_from])
                    graph_stripped.add_edge(node_to, node_from, **edge_attr)
        return graph_stripped


def find(obj, key, ignore_key='', ignore_class=(), verbose=True, visualize=True):
    builder = GraphBuilder(key=key, module=get_module_root(obj),
                           ignore_key=ignore_key, ignore_class=ignore_class)
    builder.debug = False
    builder.graph.add_node(obj, level=0)
    builder.traverse(obj)
    graph = builder.strip(types_only=False)
    if verbose:
        print(len(builder.graph))
        if len(graph) == 0:
            print("No match")
        else:
            matches = to_string(graph, source=id(obj), prefix=obj.__class__.__name__)
            print('\n'.join(matches))
    # to_pyvis(builder.graph).show('full.html')
    if visualize and len(graph) > 0:
        network_pyvis = to_pyvis(graph)
        network_pyvis.show(name=f"{obj.__class__.__name__}.html")
    return graph
