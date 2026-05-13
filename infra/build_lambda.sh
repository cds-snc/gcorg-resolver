#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/infra/.build/lambda"
OUTPUT="$PROJECT_ROOT/infra/.build/lambda.zip"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Export resolved dependencies from pyproject.toml. We skip the project itself
# (--no-emit-project) because the source is copied in directly below; installing
# the project would also force a sdist build, which --only-binary forbids.
REQUIREMENTS_FILE="$(mktemp)"
trap 'rm -f "$REQUIREMENTS_FILE"' EXIT
uv export \
  --quiet \
  --no-emit-project \
  --no-hashes \
  --extra lambda \
  --format requirements-txt \
  --output-file "$REQUIREMENTS_FILE" \
  --project "$PROJECT_ROOT"

uv pip install \
  --quiet \
  --target "$BUILD_DIR" \
  --python-platform linux \
  --python-version 3.11 \
  --only-binary :all: \
  --requirements "$REQUIREMENTS_FILE"

cp -r "$PROJECT_ROOT/src/gcorg_resolver" "$BUILD_DIR/gcorg_resolver"
cp -r "$PROJECT_ROOT/data" "$BUILD_DIR/data"

cd "$BUILD_DIR"
zip -qr "$OUTPUT" . -x '*.pyc' '__pycache__/*'
echo "Built $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
