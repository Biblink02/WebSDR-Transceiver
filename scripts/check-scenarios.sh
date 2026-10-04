#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$TASK_ROOT"
TEST_PYTHON="$TASK_ROOT/.venv/bin/python"
if [ ! -x "$TEST_PYTHON" ]; then
    printf 'Create .venv and install tests/requirements.txt first.\n' >&2
    exit 1
fi
TEST_VECTORS=$(mktemp -d)
trap 'rm -rf "$TEST_VECTORS"' EXIT
export PYTHONPATH="$TASK_ROOT/tools${PYTHONPATH:+:$PYTHONPATH}"
"$TEST_PYTHON" tests/scenario_vectors.py prepare "$TEST_VECTORS"
SCENARIO_VECTORS="$TEST_VECTORS" "${BUN_BIN:-bun}" test tests/scenarios.wasm.test.ts
"$TEST_PYTHON" tests/scenario_vectors.py verify "$TEST_VECTORS"
