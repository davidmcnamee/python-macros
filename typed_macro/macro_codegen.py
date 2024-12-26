import ast
import inspect
from typing import Any, Callable, Concatenate

from executing.executing import EnhancedAST

from typed_macro.constants import FILE_TEMPLATE
from typed_macro.util import (
    get_generated_name,
    is_absolute_import_that_doesnt_reference_macros,
)


def run_macro_and_postprocess[**P](
    func_or_class: Callable[..., Any] | type,
    source_code: str,
    proc_macro_func: Callable[Concatenate[str, P], str],
    callsite_ast: EnhancedAST,
    *args: P.args,
    **kwargs: P.kwargs,
) -> ast.Module:
    """
    Runs the user-defined macro and then runs some postprocessing steps involving:
    - omitting macro-related code from the macro-generated code
    - slightly altering the macro-generated function/class name so it doens't conflict with the original
    """
    assert isinstance(callsite_ast, ast.Call)

    try:
        new_code = proc_macro_func(inspect.getsource(func_or_class), *args, **kwargs)
        new_node = ast.parse(new_code)
        _remove_all_macro_decorator_callsites(new_node, callsite_ast)
        _copy_all_absolute_imports(
            source_code,
            new_node,
            generated_name=get_generated_name(func_or_class),
        )
        _convert_to_generated_name(new_node, func_or_class)
        return new_node
    except Exception as e:
        raise ValueError(
            "Could not parse macro-generated code as valid python code"
        ) from e


def create_type_stub(
    new_node: ast.Module, func_or_class: Callable[..., Any] | type
) -> ast.Module:
    """
    Type stubs are decoupled from runtime code because the order of operations must work like this:
    - [optional] type stubs imported (purely for ide support)
    - user-defined macro runs, generating runtime code
    - generated runtime code is executed

    If type stubs and runtime code were in the same file, then step 1 and 3 would happen at the same time,
    and you could be running stale runtime code. (It's ok for type stubs to be a bit stale)

    A type stub in this case is just the same macro-generated code, gated by `if TYPE_CHECKING:`
    """
    templ_module = ast.parse(FILE_TEMPLATE)
    assert isinstance(templ_if_stmt := templ_module.body[-1], ast.If)
    try:

        def is_not_pass(node: ast.stmt) -> bool:
            return not isinstance(node, ast.Pass)

        templ_if_stmt.body = list(filter(is_not_pass, templ_if_stmt.body))
        templ_if_stmt.orelse = list(filter(is_not_pass, templ_if_stmt.orelse))
    except ValueError:
        pass
    templ_if_stmt.body.extend(new_node.body)
    if isinstance(func_or_class, type):
        templ_if_stmt.orelse.extend(
            ast.parse(f"class {get_generated_name(func_or_class)}: pass").body
        )
    else:
        templ_if_stmt.orelse.extend(
            ast.parse(f"{get_generated_name(func_or_class)} = None").body
        )
    return templ_module


def _remove_all_macro_decorator_callsites(
    root_node: ast.Module, decorator_ast: ast.Call
) -> None:
    for node in ast.walk(root_node):
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            for dec in reversed(node.decorator_list):
                if isinstance(dec, ast.Call) and ast.unparse(dec) == ast.unparse(
                    decorator_ast
                ):
                    node.decorator_list.remove(dec)


def _convert_to_generated_name(
    node: ast.Module, func_or_class: Callable[..., Any] | type
) -> None:
    for child in ast.walk(node):
        if isinstance(child, ast.FunctionDef | ast.ClassDef) and child.name == str(
            func_or_class.__name__
        ):
            child.name = get_generated_name(func_or_class)


def _copy_all_absolute_imports(
    source_code: str, new_node: ast.Module, *, generated_name: str
) -> None:
    for node in ast.parse(source_code).body:
        if is_absolute_import_that_doesnt_reference_macros(node, generated_name) or (
            isinstance(node, ast.If)
            # sometimes top-level if statements contain imports (like `if TYPE_CHECKING:`)
            and any(
                is_absolute_import_that_doesnt_reference_macros(child, generated_name)
                for child in node.body
            )
        ):
            new_node.body.insert(0, node)
