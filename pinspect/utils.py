import inspect

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


def collect_ignored_functions():
    ignore_functions = set()
    if HAS_NUMPY:
        for func_name, func in inspect.getmembers(np.ndarray):
            ignore_functions.add(func_name)
    return ignore_functions


def get_module_root(obj):
    return obj.__class__.__module__.split('.')[0]


class IgnoreFunc:
    def __init__(self):
        self.ignored_functions = collect_ignored_functions()

    def __call__(self, obj, func_name):
        return HAS_NUMPY and isinstance(obj, np.ndarray) and func_name in self.ignored_functions
