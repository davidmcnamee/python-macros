import os
import sys
from pathlib import Path
from typing import Annotated, Iterable, Union

import libcst as cst
import typer
from git import InvalidGitRepositoryError, Repo

app = typer.Typer()

Exclude = Annotated[list[str], typer.Option(help="Paths to exclude")]


def get_git_tracked_py_files(directory: Path) -> Iterable[Path]:
    try:
        repo = Repo(directory, search_parent_directories=True)
        tracked_files = repo.git.ls_files("*.py").splitlines()
        untracked_files = repo.untracked_files
        repo_root = Path(repo.git.rev_parse("--show-toplevel"))
        return (
            repo_root / file_name
            for file_name in tracked_files + untracked_files
            if file_name.endswith(".py")
        )
    except InvalidGitRepositoryError:
        print(
            f"No Git repository found in {directory} or any parent directories.",
            file=sys.stderr,
        )
        return []


COMMONLY_EXCLUDED = [".venv"]


@app.command()
def clean(directory: Path = Path("."), exclude: Exclude = COMMONLY_EXCLUDED) -> None:
    try:
        py_files = get_git_tracked_py_files(directory)
    except InvalidGitRepositoryError:
        print("Not in a git repository, looking through all files", file=sys.stderr)
        py_files = (
            Path(root) / file
            for root, _, files in os.walk(directory)
            for file in files
            if file.endswith(".py")
        )

    for file_path in py_files:
        if any(
            str(file_path).startswith(e) or str(file_path).startswith("./" + e)
            for e in exclude
        ):
            continue
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
