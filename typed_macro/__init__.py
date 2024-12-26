"""
Heads up: this project makes heavy use of `ast` and `inspect` to parse
and modify python code. Most of this is done on mutable data structures.

It also uses the [executing](https://github.com/alexmojaki/executing)
library in places where we want to tie the results of an `inspect` frame back
to the corresponding `ast` node. 🧑‍🍳
"""

import ast
import inspect
from typing import (
    Any,
    Callable,
    Concatenate,
)

from executing.executing import Source

from typed_macro.file_writers import (
    get_or_create_macro_dir,
    write_to_runtime_file_and_import,
    write_to_stub_file,
)
from typed_macro.inline_codegen import (
    add_inline_snippets_to_callsite_file,
)
from typed_macro.macro_codegen import (
    create_type_stub,
    run_macro_and_postprocess,
)
from typed_macro.util import first_or_none


def macro[**P, T](
    proc_macro_func: Callable[Concatenate[str, P], str],
) -> Callable[Concatenate[T | None, P], Callable[..., T]]:
    def decorator_func(
        gen: T | None = None, *args: P.args, **kwargs: P.kwargs
    ) -> Callable[..., T]:
        frame_info = first_or_none(
            frame
            for frame in inspect.stack()
            if
            (
                # there is probably more exclusion logic to add here
                frame.filename != "<frozen importlib._bootstrap>"
                and not frame.filename.endswith("typed_macro/__init__.py")
            )
        )
        assert frame_info is not None, "unexpected error: could not find frame info"
        decorator_func_callsite = Source.executing(frame_info.frame)
        callsite_ast = decorator_func_callsite.node
        assert isinstance(
            callsite_ast, ast.Call
        ), "macro decorators must be called directly on a function or class!"

        def decorator(func_or_class: Callable[..., Any] | type) -> T:
            source_code = inspect.getsource(decorator_func_callsite.frame)

            # update decorator call and run codegen
            add_inline_snippets_to_callsite_file(
                func_or_class,
                source_code,
                callsite_ast,
                filename=decorator_func_callsite.frame.f_code.co_filename,
            )
            runtime_definition_ast = run_macro_and_postprocess(
                func_or_class,
                source_code,
                proc_macro_func,
                callsite_ast,
                *args,
                **kwargs,
            )
            type_stub_ast = create_type_stub(runtime_definition_ast, func_or_class)

            # write to various files
            macro_dir = get_or_create_macro_dir(decorator_func_callsite.frame)
            write_to_stub_file(macro_dir / "types.py", type_stub_ast)
            generated_func_or_class = write_to_runtime_file_and_import(
                macro_dir / f"{func_or_class.__name__}.py",
                func_or_class,
                runtime_definition_ast,
            )

            return generated_func_or_class

        return decorator

    return decorator_func
