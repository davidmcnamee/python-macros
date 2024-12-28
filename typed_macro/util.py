import ast
import threading
from datetime import datetime
from typing import Any, Callable, Iterable


def one_or_none[T](it: Iterable[T]) -> T | None:
    iterator = iter(it)
    first = next(iterator, None)

    class Sentinel:
        pass

    SENTINEL = Sentinel()
    assert (
        next(iterator, SENTINEL) is SENTINEL
    ), "found more than one result when one or none was expected"
    return first


def first_or_none[T](it: Iterable[T]) -> T | None:
    return next(iter(it), None)


def get_file_pos_from_line_col(lineno: int, col_offset: int, file_contents: str) -> int:
    lineno -= 1  # adjust for zero-index
    # (weirdly, col_offset is already zero-indexed by ast library)
    lines = file_contents.splitlines(keepends=True)
    return sum(len(line) for line in lines[:lineno]) + col_offset


def get_generated_name(func_or_class: Callable[..., Any] | type) -> str:
    if isinstance(func_or_class, type):
        return f"Gen{func_or_class.__name__}"
    else:
        return f"gen_{func_or_class.__name__}"


def is_absolute_import_that_doesnt_reference_macros(
    node: ast.stmt, generated_name: str
) -> bool:
    return (
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and not (
            "__macro__.types" in ast.unparse(node)
            and generated_name in [alias.name for alias in node.names]
        )
    ) or isinstance(node, ast.Import)


def debounce[T](delay: float) -> Callable[[Callable[[T], None]], Callable[[T], None]]:
    def _debounce(func: Callable[[T], None]) -> Callable[[T], None]:
        last_call_time: dict[T, datetime] = {}

        def flush(arg: T, called_at: datetime) -> None:
            nonlocal last_call_time
            if last_call_time[arg] > called_at:
                return  # no-op
            func(arg)

        def wrapper(arg: T) -> None:
            last_call_time[arg] = datetime.now()
            threading.Timer(delay, flush, args=(arg, datetime.now())).start()

        return wrapper

    return _debounce
