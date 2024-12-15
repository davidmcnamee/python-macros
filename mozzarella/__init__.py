import importlib
import inspect
import re
import sys
from inspect import FrameInfo, getsource, stack
from pathlib import Path
from typing import Callable, Concatenate, ParamSpec

FILE_PREFIX = '''
"""
THIS FILE IS GENERATED BY A MACRO. DO NOT EDIT.
"""
'''.lstrip()

generated_files = set()


def replace(original_str: str, start_idx: int, end_idx: int, new_str: str) -> str:
    return original_str[:start_idx] + new_str + original_str[end_idx:]


# this code is gross, badly needs a refactor
def import_generated_func(
    source_code: str, decorator_frame: FrameInfo, func_name: str
) -> str:
    source_code_lines = source_code.splitlines()
    assert (
        len(decorator_frame.code_context) == 1
    ), "unexpected number of code contexts, this should never happen"
    callsite_code = decorator_frame.code_context[0]
    if not callsite_code.startswith("@"):
        raise ValueError(
            "this macro can only be used as a decorator (when it is called, it must be prefixed with @)"
        )

    positions = decorator_frame.positions

    start_row, start_col = positions.lineno - 1, positions.col_offset - 1
    end_row, end_col = positions.end_lineno - 1, positions.end_col_offset
    start_idx = sum(len(line) + 1 for line in source_code_lines[:start_row]) + start_col
    end_idx = sum(len(line) + 1 for line in source_code_lines[:end_row]) + end_col
    if "generated=" not in callsite_code:
        before, after = callsite_code.strip().split("(", maxsplit=1)
        import_stmt = f"from .__macros__ import {func_name}\n"
        callsite_code = f"{before}(generated={func_name},{after}"
        updated_source_code = replace(source_code, start_idx, end_idx, callsite_code)
        with open(decorator_frame.filename, "w") as f:
            f.write(import_stmt + updated_source_code)


P = ParamSpec("P")


# this code is gross, badly needs a refactor
def macro():
    def _macro(proc_macro_func: Callable[Concatenate[str, P], str]):
        def decorator_func[T](
            *args: P.args, generated: T | None = None, **kwargs: P.kwargs
        ) -> Callable[..., T]:
            source_code = getsource(inspect.currentframe().f_back)
            decorator_frame = stack()[-3]
            # TODO: could use `__session__ or __vsc_ipynb_file__` to determine file name of jupyter notebook
            # https://github.com/jupyterlab/jupyterlab/issues/16282

            def decorator(func: Callable) -> T:
                global generated_files
                new_code = proc_macro_func(getsource(func), *args, **kwargs)
                new_code = re.sub(
                    rf"@{proc_macro_func.__name__}\(.*?\)", "", new_code, count=1
                )
                generated_file_path = (
                    Path(decorator_frame.filename).parent / "__macros__.py"
                )

                if generated_file_path not in generated_files:
                    with open(generated_file_path, "w") as f:
                        f.write(FILE_PREFIX)
                    generated_files.add(generated_file_path)

                with open(generated_file_path, "a") as f:
                    f.write(new_code + "\n")

                import_generated_func(source_code, decorator_frame, func.__name__)

                __macros__ = import_from_path("__macros__", generated_file_path)
                return getattr(__macros__, func.__name__)

            return decorator

        return decorator_func

    return _macro


def import_from_path(module_name, file_path):
    """https://docs.python.org/3/library/importlib.html#importing-programmatically"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
