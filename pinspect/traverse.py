import contextlib
import inspect
import logging
import re
import uuid
from pprint import pformat

import networkx as nx
from tqdm import tqdm

from pinspect.logger import init_logger
from pinspect.utils import get_module_root, IgnoreFunc, REGEX_NEVER_MATCH, NON_EXECUTABLE, to_pyvis, to_string, \
    check_edge

init_logger()


class DiGraphAcyclic(nx.DiGraph):
    def add_edge(self, u_of_edge, v_obj, label=None, **attr):
        v_of_edge = self.add_node(v_obj, level=self.nodes[u_of_edge]['level'] + 1)
        if nx.has_path(self, v_of_edge, u_of_edge):
            # makes cycle
            return False
        if label.endswith('()'):
            color = 'red'
        elif self.nodes[v_of_edge]['level'] < self.nodes[u_of_edge]['level']:
            # level up
            color = 'magenta'
        else:
            color = None
        super().add_edge(u_of_edge, v_of_edge, label=label, color=color, **attr)
        return True

    def add_node(self, obj, **attr):
        if isinstance(obj, Exception):
            obj_id = uuid.uuid4().hex
            color = 'red'
        else:
            obj_id = id(obj)
            color = None
        if obj_id in self.nodes:
            return obj_id
        label = obj.__class__.__name__
        if isinstance(obj, (set, list, tuple, dict)):
            label = f"{label} of size {len(obj)}"
        title = pformat(obj, depth=1, compact=True)
        title = title.splitlines()
        title_short = title[0]
        if len(title) > 1:
            title_short = f"{title_short} ..., {title[-1]}"
        title_short = title_short.strip('<>')
        super().add_node(obj_id, label=label, title=title_short, color=color, **attr)
        return obj_id


class GraphBuilder:
    def __init__(self, obj, key, ignore_key='', ignore_class=()):
        if key == '':
            key = REGEX_NEVER_MATCH
        self.obj = obj
        self.obj_saved = []  # prevent being collected by GC
        self.key = re.compile(key, flags=re.IGNORECASE)
        self.graph = DiGraphAcyclic()
        self.module = get_module_root(obj)
        nonexec = NON_EXECUTABLE
        if ignore_key:
            nonexec = f"{nonexec}|{ignore_key}"
        self.nonexec = re.compile(nonexec)
        self.ignore_attribute = IgnoreFunc(key=ignore_key, obj_class=ignore_class)
        self.tried_functions = set()
        self.tried_classes = set()
        self.max_depth = 10

        self.graph.add_node(obj, level=0)

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

        logging.debug(f"{'  ' * level}Inspecting {obj.__class__.__name__} (level={level}): {obj}")

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
                    logging.debug(f"{'  ' * (level + 1)}Executing {obj.__class__.__name__}.{attr_name}()")
                    with contextlib.redirect_stdout(None):
                        res = attr()
                except Exception as err:
                    # create a new exception to make sure the id is unique
                    err = err.__class__(str(err))
                    self.graph.add_edge(id(obj), err, label=f"{attr_name}()")
                else:
                    self.obj_saved.append(res)
                    self.tried_functions.add(full_name)
                    self.traverse(res, parent_edge=(obj, f"{attr_name}()"), level=level + 1)
            elif not inspect.ismethod(attr):
                self.traverse(attr, parent_edge=(obj, attr_name), level=level + 1)

    def strip(self, with_methods=True):
        graph = self.graph.reverse(copy=False)
        graph_stripped = nx.DiGraph()
        for node_from in nx.topological_sort(graph):
            if self.key.search(graph.nodes[node_from].get('label', '')):
                graph.nodes[node_from]['color'] = 'green'
                include_parents = True
            else:
                include_parents = graph.nodes[node_from].get('include', False)
            for node_to, edge_attr in graph.adj[node_from].items():
                method_hit = with_methods and self.key.search(edge_attr['label'])
                if include_parents or method_hit:
                    graph.nodes[node_to]['include'] = True
                    graph_stripped.add_node(node_to, **graph.nodes[node_to])
                    graph_stripped.add_node(node_from, **graph.nodes[node_from])
                    graph_stripped.add_edge(node_to, node_from, **edge_attr)
        graph_stripped.nodes[id(self.obj)]['color'] = 'blue'
        return graph_stripped


def find(obj, key, ignore_key='', ignore_class=(), verbose=True, visualize=True):
    builder = GraphBuilder(obj, key=key, ignore_key=ignore_key, ignore_class=ignore_class)
    builder.traverse(obj)
    builder.obj_saved.clear()
    graph = builder.strip(with_methods=True)
    logging.info(f"Stripped graph length: {len(builder.graph)} -> {len(graph)}")
    if verbose:
        if len(graph) == 0:
            print("No match")
        else:
            matches = to_string(graph, source=id(obj), prefix=obj.__class__.__name__)
            print('\n'.join(matches))
    # to_pyvis(builder.graph, layout=False).show('full.html')
    if visualize and len(graph) > 0:
        network_pyvis = to_pyvis(graph)
        network_pyvis.show(name=f"{obj.__class__.__name__}.html")
    return graph
