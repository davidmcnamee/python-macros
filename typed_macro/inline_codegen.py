import ast
import atexit
import re
from itertools import chain, groupby
from typing import Any, Callable, Iterable

from executing.executing import EnhancedAST

from typed_macro.util import (
    first_or_none,
    get_file_pos_from_line_col,
    get_generated_name,
    is_absolute_import_that_doesnt_reference_macros,
    one_or_none,
)

insert_statements: list[tuple[str, int, str]] = []


def insert_all_statements() -> None:
    insert_statements.sort(reverse=True)
    for filename, group in groupby(insert_statements, key=lambda x: x[0]):
        group = list(group)
        with open(filename, "r") as f:
            source_code = f.read()
        for _, pos, insert_str in group:
            source_code = source_code[:pos] + insert_str + source_code[pos:]
        with open(filename, "w") as f:
            f.write(source_code)


atexit.register(insert_all_statements)


def add_inline_snippets_to_callsite_file(
    func_or_class: Callable[..., Any] | type,
    source_code: str,
    callsite_ast: EnhancedAST,
    *,
    filename: str,
) -> None:
    """
    There are some code snippets that we need to add directly to the file where
    the macro decorator was called. This function takes the original source code
    and returns the modified source code with those snippets added.
    """
    insert_statements.extend(
        (filename, pos, insert_str)
        for pos, insert_str in _maybe_insert_gen_kwarg_to_callsite_func_decorator(
            func_or_class, callsite_ast, source_code
        )
    )
    insert_statements.extend(
        (filename, pos, insert_str)
        for pos, insert_str in _maybe_insert_imports_to_macro_type_stubs(
            func_or_class, callsite_ast, source_code
        )
    )


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
        if not is_absolute_import_that_doesnt_reference_macros(
            node, generated_name
        ) and re.search(r"(\W|^)" + generated_name + r"(\W|$)", ast.unparse(node)):
            return  # early return if already imported
    yield 0, f"from .__macro__.types import {generated_name}\n"


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
        arg
        for arg in callsite_ast.args
        if ast.unparse(arg) == get_generated_name(func_or_class)
    ):
        first_arg = first_or_none(chain(callsite_ast.args, callsite_ast.keywords))
        insert_str = get_generated_name(func_or_class)
        if first_arg is not None:
            insert_pos = get_file_pos_from_line_col(
                first_arg.lineno,
                first_arg.col_offset,
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
