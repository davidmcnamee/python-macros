import os
import shutil
import sys
from pathlib import Path
from typing import Annotated, Union

import libcst as cst
import typer

app = typer.Typer()

Exclude = Annotated[list[str], typer.Option(help="Paths to exclude")]


@app.command()
def clean(
    directory: Path = Path("."), exclude: Exclude = [".venv", "node_modules", ".git"]
) -> None:
    for root, _, files in os.walk(directory):
        if any(root.startswith(e) or root.startswith("./" + e) for e in exclude):
            continue
        for file_name in files:
            if file_name.endswith("__macro__"):
                shutil.rmtree(Path(root) / file_name)
            if file_name.endswith(".py"):
                file_path = Path(root) / file_name
                remove_macro_references(file_path)


@app.command(hidden=True)
def dummy() -> None:
    pass  # need a 2nd subcommand, or else typer will only allow `macro` instead of `macro clean`


def remove_macro_references(file_path: Path) -> None:
    with open(file_path, "r") as f:
        content = f.read()
    module = cst.parse_module(content)
    updated_tree = module.visit(CleanerUpper(module))
    if updated_tree.code != module.code:
        print(f"Updated {file_path}", file=sys.stderr)
        with open(file_path, "w") as f:
            f.write(updated_tree.code)


class CleanerUpper(cst.CSTTransformer):
    def __init__(self, module: cst.Module) -> None:
        self.symbols_to_remove: set[str] = set()
        self.module = module

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[
        cst.BaseSmallStatement,
        cst.FlattenSentinel[cst.BaseSmallStatement],
        cst.RemovalSentinel,
    ]:
        if "__macro__" in self.module.code_for_node(original_node) and isinstance(
            original_node.names, tuple
        ):
            for name in original_node.names:
                self.symbols_to_remove.add(name.evaluated_name)
            return cst.RemoveFromParent()
        return updated_node

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        if (
            original_node.args
            and isinstance(name := original_node.args[0].value, cst.Name)
            and name.value in self.symbols_to_remove
        ):
            return updated_node.with_changes(
                args=updated_node.args[1:]
            )  # remove macro-generated type args
        return updated_node


def main() -> None:
    app()
