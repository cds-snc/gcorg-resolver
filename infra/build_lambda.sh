#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/infra/.build/lambda"
OUTPUT="$PROJECT_ROOT/infra/.build/lambda.zip"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

uv pip install \
  --quiet \
  --target "$BUILD_DIR" \
  --python-platform linux \
  --python-version 3.11 \
  --only-binary :all: \
  "$PROJECT_ROOT[lambda]"

cp -r "$PROJECT_ROOT/src/gcorg_resolver" "$BUILD_DIR/gcorg_resolver"
cp -r "$PROJECT_ROOT/data" "$BUILD_DIR/data"

cd "$BUILD_DIR"
zip -qr "$OUTPUT" . -x '*.pyc' '__pycache__/*'
echo "Built $OUTPUT ($(du -h "$OUTPUT" | cut -f1))"
