import contextlib
import inspect
import re
from collections import namedtuple
from pprint import pformat
import builtins

import networkx as nx

from pinspect.utils import get_module_root, IgnoreFunc, REGEX_NEVER_MATCH, NON_EXECUTABLE, to_pyvis, to_string

Match = namedtuple("Match", ("attributes", "classes"))


class DiGraphAcyclic(nx.DiGraph):
    def add_edge(self, u_of_edge, v_obj, **attr):
        v_of_edge = id(v_obj)
        if v_of_edge not in self.nodes:
            level = self.nodes[u_of_edge]['level'] + 1
            self.add_node(v_obj, level=level)
        if nx.has_path(self, v_of_edge, u_of_edge):
            return False
        super().add_edge(u_of_edge, v_of_edge, **attr)
        return True

    def add_node(self, obj, **attr):
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
        self.graph = DiGraphAcyclic()

    def traverse(self, obj, prefix='', level=0):
        if get_module_root(obj) != self.module:
            return Match([], [])
        if obj.__class__ in self.tried_classes:
            return Match([], [])
        self.tried_classes.add(obj.__class__)
        found_attrs, found_class = [], []
        obj_class = obj.__class__.__name__
        if self.key.search(obj_class):
            found_class.append(f"{prefix} -> {obj_class}")
        self.graph.add_node(obj, level=level)
        for attr_name in dir(obj):
            if attr_name.startswith('__'):
                continue
            if self.ignore_attribute(obj, attr_name):
                continue
            attr = getattr(obj, attr_name)
            is_method = inspect.ismethod(attr)
            if self.key.search(attr_name):
                # if is_method:
                #     attr_name = attr_name + str(inspect.signature(attr))
                found_attrs.append(f"{prefix}.{attr_name}")
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
                    internal_attrs, internal_cls = self.traverse(res, prefix=f"{prefix}.{attr_name}()",
                                                                 level=level+1)
                    found_attrs.extend(internal_attrs)
                    found_class.extend(internal_cls)
            if isinstance(attr, (set, list, tuple)):
                if len(attr) > 0:
                    attr = next(iter(attr))
                    if not self.graph.add_edge(id(obj), attr, label=f"{attr_name}[0]"):
                        continue
                    internal_attrs, internal_cls = self.traverse(attr, prefix=f"{prefix}.{attr_name}[0]",
                                                                 level=level+1)
                    found_attrs.extend(internal_attrs)
                    found_class.extend(internal_cls)
                else:
                    self.graph.add_edge(id(obj), attr, label=attr_name)
            elif not is_method:
                if not self.graph.add_edge(id(obj), attr, label=attr_name):
                    continue
                internal_attrs, internal_cls = self.traverse(attr, prefix=f"{prefix}.{attr_name}",
                                                             level=level+1)
                found_attrs.extend(internal_attrs)
                found_class.extend(internal_cls)
        return Match(found_attrs, found_class)

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
    matches = builder.traverse(obj, prefix=obj.__class__.__name__)
    graph = builder.strip()
    if verbose:
        matches2 = to_string(graph, source=id(obj), prefix=obj.__class__.__name__)
        print('\n'.join(matches2))
        if len(matches.attributes) > 0:
            print(">>> Methods and attributes", '\n'.join(matches.attributes), sep='\n')
        if len(matches.classes) > 0:
            print(">>> Object classes", '\n'.join(matches.classes), sep='\n')
    # if visualize:
    #     network_pyvis = to_pyvis(graph)
    #     network_pyvis.show(name=f"{obj.__class__.__name__}.html")
    return matches
