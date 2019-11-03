import inspect
import re

from pinspect.utils import get_module_root, StdoutIgnore, IgnoreFunc


class InspectInfo:
    def __init__(self, key, module, ignore="save|write|remove|delete"):
        self.pattern = re.compile(key)
        self.module = module
        self.ignore = re.compile(ignore)
        self.ignore_function = IgnoreFunc()
        self.tried_functions = set()
        self.tried_ids = set()


def _find_children(obj, info: InspectInfo, prefix=''):
    if get_module_root(obj) != info.module:
        return []
    if id(obj) in info.tried_ids:
        return []
    info.tried_ids.add(id(obj))
    found = []
    for attr_name in dir(obj):
        if info.ignore_function(obj, attr_name):
            continue
        attr = getattr(obj, attr_name)
        is_method = inspect.ismethod(attr)
        if info.pattern.search(attr_name):
            if is_method:
                attr_name = attr_name + str(inspect.signature(attr))
            found.append(f"{prefix}.{attr_name}")

        full_name = f"{obj.__class__.__name__}.{attr_name}"
        if is_method and full_name not in info.tried_functions and not info.ignore.search(attr_name):
            try:
                with StdoutIgnore():
                    res = attr()
                info.tried_functions.add(full_name)
                internal_matches = _find_children(res, info=info, prefix=f"{prefix}.{attr_name}()")
                found.extend(internal_matches)
            except Exception as err:
                pass
        if isinstance(attr, (list, tuple)) and len(attr) > 0:
            internal_matches = _find_children(attr[0], info=info, prefix=f"{prefix}.{attr_name}[0]")
            found.extend(internal_matches)
    return found


def find(obj, key):
    info = InspectInfo(key=key, module=get_module_root(obj))
    match = _find_children(obj, info=info, prefix=obj.__class__.__name__)
    return match
