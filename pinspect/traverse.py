import inspect
import re
from collections import namedtuple

import networkx as nx
from pinspect.utils import get_module_root, StdoutIgnore, IgnoreFunc, REGEX_NEVER_MATCH

Match = namedtuple("Match", ("attributes", "classes"))


class DiGraphAcyclic(nx.DiGraph):
    def __init__(self, **attr):
        super().__init__(**attr)

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        if nx.has_path(self, v_of_edge, u_of_edge):
            print('exists')
            return False
        super().add_edge(u_of_edge=u_of_edge, v_of_edge=v_of_edge, **attr)
        return True


class GraphBuilder:
    def __init__(self, key, module, non_executable="save|write|remove|delete"):
        if key == '':
            key = REGEX_NEVER_MATCH
        self.key = re.compile(key, flags=re.IGNORECASE)
        self.module = module
        self.nonexec = re.compile(non_executable)
        self.ignore_function = IgnoreFunc()
        self.tried_functions = set()
        # self.tried_ids = set()
        self.graph = DiGraphAcyclic()

    def traverse(self, obj, prefix=''):
        if get_module_root(obj) != self.module:
            return Match([], [])
        # if id(obj) in info.tried_ids:
        #     return Match([], [])
        found_attrs, found_class = [], []
        obj_class = obj.__class__.__name__
        if self.key.search(obj_class):
            found_class.append(f"{prefix} -> {obj_class}")
        # info.tried_ids.add(id(obj))
        self.graph.add_node(id(obj))
        for attr_name in dir(obj):
            if attr_name.startswith('__'):
                continue
            if self.ignore_function(obj, attr_name):
                continue
            attr = getattr(obj, attr_name)
            is_method = inspect.ismethod(attr)
            if self.key.search(attr_name):
                if is_method:
                    attr_name = attr_name + str(inspect.signature(attr))
                found_attrs.append(f"{prefix}.{attr_name}")

            full_name = f"{obj.__class__.__name__}.{attr_name}"
            if is_method and full_name not in self.tried_functions and not self.nonexec.search(attr_name):
                try:
                    with StdoutIgnore():
                        res = attr()
                    self.tried_functions.add(full_name)
                    if not self.graph.add_edge(id(obj), id(res), label=attr_name):
                        continue
                    internal_attrs, internal_cls = self.traverse(res, prefix=f"{prefix}.{attr_name}()")
                    found_attrs.extend(internal_attrs)
                    found_class.extend(internal_cls)
                except Exception:
                    pass
            if isinstance(attr, (list, tuple)) and len(attr) > 0:
                internal_attrs, internal_cls = self.traverse(attr[0], prefix=f"{prefix}.{attr_name}[0]")
                found_attrs.extend(internal_attrs)
                found_class.extend(internal_cls)
            elif not is_method:
                internal_attrs, internal_cls = self.traverse(attr, prefix=f"{prefix}.{attr_name}")
                found_attrs.extend(internal_attrs)
                found_class.extend(internal_cls)
        return Match(found_attrs, found_class)


def find(obj, key, verbose=True):
    builder = GraphBuilder(key=key, module=get_module_root(obj))
    matches = builder.traverse(obj, prefix=obj.__class__.__name__)
    if verbose:
        if len(matches.attributes) > 0:
            print(">>> Methods and attributes", '\n'.join(matches.attributes), sep='\n')
        if len(matches.classes) > 0:
            print(">>> Object classes", '\n'.join(matches.classes), sep='\n')
    return matches
