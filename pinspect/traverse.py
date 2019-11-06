import inspect
import re
from collections import namedtuple

from pinspect.utils import get_module_root, StdoutIgnore, IgnoreFunc, REGEX_NEVER_MATCH

Match = namedtuple("Match", ("attributes", "classes"))


class InspectInfo:
    def __init__(self, key, module, non_executable="save|write|remove|delete"):
        if key == '':
            key = REGEX_NEVER_MATCH
        self.key = re.compile(key, flags=re.IGNORECASE)
        self.module = module
        self.nonexec = re.compile(non_executable)
        self.ignore_function = IgnoreFunc()
        self.tried_functions = set()
        self.tried_ids = set()


def _find_children(obj, info: InspectInfo, prefix=''):
    if get_module_root(obj) != info.module:
        return Match([], [])
    if id(obj) in info.tried_ids:
        return Match([], [])
    found_attrs, found_class = [], []
    obj_class = obj.__class__.__name__
    if info.key.search(obj_class):
        found_class.append(f"{prefix} -> {obj_class}")
    info.tried_ids.add(id(obj))
    for attr_name in dir(obj):
        if attr_name.startswith('__'):
            continue
        if info.ignore_function(obj, attr_name):
            continue
        attr = getattr(obj, attr_name)
        is_method = inspect.ismethod(attr)
        if info.key.search(attr_name):
            if is_method:
                attr_name = attr_name + str(inspect.signature(attr))
            found_attrs.append(f"{prefix}.{attr_name}")

        full_name = f"{obj.__class__.__name__}.{attr_name}"
        if is_method and full_name not in info.tried_functions and not info.nonexec.search(attr_name):
            try:
                with StdoutIgnore():
                    res = attr()
                info.tried_functions.add(full_name)
                internal_attrs, internal_cls = _find_children(res, info=info, prefix=f"{prefix}.{attr_name}()")
                found_attrs.extend(internal_attrs)
                found_class.extend(internal_cls)
            except Exception:
                pass
        if isinstance(attr, (list, tuple)) and len(attr) > 0:
            internal_attrs, internal_cls = _find_children(attr[0], info=info, prefix=f"{prefix}.{attr_name}[0]")
            found_attrs.extend(internal_attrs)
            found_class.extend(internal_cls)
        elif not is_method:
            internal_attrs, internal_cls = _find_children(attr, info=info, prefix=f"{prefix}.{attr_name}")
            found_attrs.extend(internal_attrs)
            found_class.extend(internal_cls)
    return Match(found_attrs, found_class)


def find(obj, key, verbose=True):
    info = InspectInfo(key=key, module=get_module_root(obj))
    matches = _find_children(obj, info=info, prefix=obj.__class__.__name__)
    if verbose:
        if len(matches.attributes) > 0:
            print(">>> Methods and attributes", '\n'.join(matches.attributes), sep='\n')
        if len(matches.classes) > 0:
            print(">>> Object classes", '\n'.join(matches.classes), sep='\n')
    return matches
