import ast
import importlib
import sys
from pathlib import Path
from types import FrameType
from typing import Any, Callable

from typed_macro.constants import FILE_PREFIX
from typed_macro.util import get_generated_name

_generated_files = set[Path]()


def write_to_runtime_file_and_import(
    runtime_file: Path, func_or_class: Callable[..., Any] | type, new_node: ast.Module
) -> Any:
    with runtime_file.open("w") as f:
        f.write(FILE_PREFIX + ast.unparse(new_node) + "\n\n")

    new_module = _import_from_path(
        f".__macros__.{func_or_class.__name__}",
        runtime_file.as_posix(),
    )
    return getattr(new_module, get_generated_name(func_or_class))


def write_to_stub_file(stub_file: Path, templ_module: ast.Module) -> None:
    global _generated_files

    if stub_file not in _generated_files:
        with stub_file.open("w") as f:
            f.write(FILE_PREFIX)
        _generated_files.add(stub_file)

    with stub_file.open("a") as f:
        f.write(ast.unparse(templ_module) + "\n\n")


def get_or_create_macro_dir(frame: FrameType) -> Path:
    macro_dir = Path(frame.f_code.co_filename).parent / "__macros__"
    if not macro_dir.exists():
        macro_dir.mkdir(parents=True)
    return macro_dir


def _import_from_path(module_name: str, file_path: str) -> Any:
    """https://docs.python.org/3/library/importlib.html#importing-programmatically"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)  # type: ignore
    module = importlib.util.module_from_spec(spec)  # type: ignore
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore
    return module  # type: ignore
