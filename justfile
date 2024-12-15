
set dotenv-load := true

test:
    uv run python -m tests.proc_macro

publish:
    rm -rf *.egg-info dist
    uv build
    uv publish
