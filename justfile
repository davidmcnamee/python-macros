
set dotenv-load := true

test:
    uv run python -m tests.proc_macro

itest:
    watchexec -e py -i '*/__macro__/*' just test

publish:
    rm -rf *.egg-info dist
    uv build
    uv publish

lint:
    uv run ruff check --fix --unsafe-fixes
    uv run ruff format
