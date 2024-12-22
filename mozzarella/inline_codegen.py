import ast
import re
from typing import Any, Callable, Iterable

from executing.executing import EnhancedAST

from mozzarella.util import (
    first_or_none,
    get_file_pos_from_line_col,
    get_generated_name,
    is_absolute_import,
    one_or_none,
)


def add_inline_snippets_to_callsite_file(
    func_or_class: Callable[..., Any] | type,
    source_code: str,
    callsite_ast: EnhancedAST,
) -> str:
    """
    There are some code snippets that we need to add directly to the file where
    the macro decorator was called. This function takes the original source code
    and returns the modified source code with those snippets added.
    """
    insert_statements: list[tuple[int, str]] = sorted(
        [
            *_maybe_insert_gen_kwarg_to_callsite_func_decorator(
                func_or_class, callsite_ast, source_code
            ),
            *_maybe_insert_imports_to_macro_type_stubs(
                func_or_class, callsite_ast, source_code
            ),
        ],
        reverse=True,
    )

    for pos, insert_str in insert_statements:
        source_code = source_code[:pos] + insert_str + source_code[pos:]
    return source_code


def _maybe_insert_imports_to_macro_type_stubs(
    func_or_class: Callable[..., Any] | type,
    callsite_ast: EnhancedAST,
    source_code: str,
) -> Iterable[tuple[int, str]]:
    """
    The macro can't depend on any variables or functions defined in the file
    where it was called, but it can depend on any *absolute* imports from the
    file where it was called.
    """
    assert isinstance(callsite_ast, ast.Call)
    generated_name = get_generated_name(func_or_class)
    for node in ast.parse(source_code).body:
        if not is_absolute_import(node) and re.search(
            r"(\W|^)" + generated_name + r"(\W|$)", ast.unparse(node)
        ):
            return  # early return if already imported
    yield 0, f"from .__macros__.types import {generated_name}\n"


def _maybe_insert_gen_kwarg_to_callsite_func_decorator(
    func_or_class: Callable[..., Any] | type,
    callsite_ast: EnhancedAST,
    source_code: str,
) -> Iterable[tuple[int, str]]:
    """
    In cases where we're decorating a function, we need to insert the `gen=...` kwarg
    so that your code editor can use the macro-generated code for type checking.

    Note: avoiding `ast.unparse(...)` because it won't preserve comments or whitespace.
    """
    assert isinstance(callsite_ast, ast.Call)
    if isinstance(
        callsite_ast.parent, ast.FunctionDef | ast.ClassDef
    ) and not one_or_none(
        kwarg for kwarg in callsite_ast.keywords if kwarg.arg == "gen"
    ):
        first_kwarg = first_or_none(callsite_ast.keywords)
        insert_str = f"gen={get_generated_name(func_or_class)}"
        if first_kwarg is not None:
            insert_pos = get_file_pos_from_line_col(
                first_kwarg.lineno,
                first_kwarg.col_offset,
                source_code,
            )
            insert_str = insert_str + ", "
        else:
            assert callsite_ast.end_lineno is not None
            assert callsite_ast.end_col_offset is not None
            insert_pos = (
                get_file_pos_from_line_col(
                    callsite_ast.end_lineno,
                    callsite_ast.end_col_offset,
                    source_code,
                )
                - 1  # just before the close parenth at the end of the function call
            )

        yield insert_pos, insert_str
