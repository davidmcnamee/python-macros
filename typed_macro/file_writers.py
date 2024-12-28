import ast
import importlib
import logging
import sys
from collections import defaultdict
from pathlib import Path
from types import FrameType
from typing import Any, Callable

from typed_macro.constants import FILE_PREFIX
from typed_macro.util import debounce, get_generated_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

stub_file_snippets: dict[Path, list[str]] = defaultdict(list)


@debounce(delay=1)
def _flush_stub_file_snippets(stub_file: Path) -> None:
    contents = FILE_PREFIX + "\n\n".join(stub_file_snippets[stub_file])
    stub_file_snippets[stub_file] = []
    _write_to_file_if_changes(stub_file, contents)


def write_to_runtime_file_and_import(
    runtime_file: Path, func_or_class: Callable[..., Any] | type, new_node: ast.Module
) -> Any:
    _write_to_file_if_changes(
        runtime_file, FILE_PREFIX + ast.unparse(new_node) + "\n\n"
    )

    new_module = _import_from_path(
        f".__macro__.{func_or_class.__name__}",
        runtime_file.as_posix(),
    )
    return getattr(new_module, get_generated_name(func_or_class))


def write_to_stub_file(stub_file: Path, templ_module: ast.Module) -> None:
    stub_file_snippets[stub_file].append(ast.unparse(templ_module))
    _flush_stub_file_snippets(stub_file)


def get_or_create_macro_dir(frame: FrameType) -> Path:
    macro_dir = Path(frame.f_code.co_filename).parent / "__macro__"
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


def _write_to_file_if_changes(file_path: Path, content: str) -> None:
    if file_path.exists():
        with open(file_path, "r") as f:
            cur_content = f.read()
        if ast.unparse(ast.parse(cur_content)) == ast.unparse(ast.parse(content)):
            return  # no changes, skip writing (to avoid unnecessary reloads in `uvicorn --reload` projects)

    with open(file_path, "w") as f:
        f.write(content)
