import contextlib
import inspect
import re
from collections import namedtuple
from pprint import pformat
from tqdm import tqdm

import networkx as nx

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
    def __init__(self, key, module, ignore=''):
        if key == '':
            key = REGEX_NEVER_MATCH
        self.key = re.compile(key, flags=re.IGNORECASE)
        self.module = module
        self.nonexec = re.compile(f"{NON_EXECUTABLE}|{ignore}")
        self.ignore_attribute = IgnoreFunc(ignore)
        self.tried_functions = set()
        self.tried_classes = set()
        self.max_depth = 10
        self.graph = DiGraphAcyclic()

    def traverse(self, obj, level=0):
        if level >= self.max_depth:
            return
        if not isinstance(obj, (list, tuple, set, dict)):
            # don't skip builtins like list, tuple, set, dict
            if get_module_root(obj) != self.module or obj.__class__ in self.tried_classes:
                return
            self.tried_classes.add(obj.__class__)
        if not self.graph.add_node(obj, level=level):
            # already added
            pass
            # return
        #
        # if isinstance(obj, dict):
        #     for key, value in obj.items():
        #         if not self.graph.add_edge(id(obj), value, label=f"['{key}']"):
        #             continue
        #         self.traverse(value, level=level + 1)
        #     return
        # if isinstance(obj, (set, list, tuple)):

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
            is_method = callable(attr)
            if isinstance(attr, (bool, int, str, float, type)):
                if self.key.search(attr_name):
                    self.graph.add_edge(id(obj), attr, label=attr_name)
                continue

            full_name = f"{obj.__class__.__name__}.{attr_name}"
            if is_method and full_name not in self.tried_functions and not self.nonexec.search(attr_name):
                try:
                    with contextlib.redirect_stdout(None):
                        res = attr()
                except Exception:
                    pass
                else:
                    self.tried_functions.add(full_name)
                    if not self.graph.add_edge(id(obj), res, label=f"{attr_name}()"):
                        continue
                    self.traverse(res, level=level + 1)
            if isinstance(attr, (set, list, tuple)):
                if len(attr) > 0:
                    attr = next(iter(attr))
                    if not self.graph.add_edge(id(obj), attr, label=f"{attr_name}[0]"):
                        continue
                    self.traverse(attr, level=level + 1)
                else:
                    self.graph.add_edge(id(obj), attr, label=attr_name)
            elif not is_method:
                if not self.graph.add_edge(id(obj), attr, label=attr_name):
                    continue
                self.traverse(attr, level=level + 1)

    def strip(self):
        graph = self.graph.reverse(copy=False)
        graph_stripped = nx.DiGraph()
        for node_from in nx.topological_sort(graph):
            if self.key.search(graph.nodes[node_from].get('label', '')):
                include_parents = True
            else:
                include_parents = graph.nodes[node_from].get('include', False)
            for node_to, edge_attr in graph.adj[node_from].items():
                if include_parents or self.key.search(edge_attr['label']):
                    graph.nodes[node_to]['include'] = True
                    graph_stripped.add_node(node_to, **graph.nodes[node_to])
                    graph_stripped.add_node(node_from, **graph.nodes[node_from])
                    graph_stripped.add_edge(node_to, node_from, **edge_attr)
        return graph_stripped


def find(obj, key, verbose=True, ignore='', visualize=True):
    builder = GraphBuilder(key=key, module=get_module_root(obj), ignore=ignore)
    builder.traverse(obj)
    graph = builder.strip()
    if verbose:
        matches = to_string(graph, source=id(obj), prefix=obj.__class__.__name__)
        print('\n'.join(matches))
    if visualize:
        network_pyvis = to_pyvis(graph)
        network_pyvis.show(name=f"{obj.__class__.__name__}.html")
    return graph
