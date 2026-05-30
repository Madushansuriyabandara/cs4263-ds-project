#!/bin/bash
# Helper script to build the final submission zip.
# Usage: ./package.sh

set -e
NAME="210146N-210626L"
STAGING_DIR="$NAME"

echo "📦 Building submission zip: ${NAME}.zip"

# Clean previous build
rm -rf "$STAGING_DIR" "${NAME}.zip"
mkdir -p "$STAGING_DIR"

# Copy required artifacts
cp -r src/        "$STAGING_DIR/"
cp -r inputs/     "$STAGING_DIR/"
cp -r outputs/    "$STAGING_DIR/"
cp -r diagrams/   "$STAGING_DIR/"
cp README.md requirements.txt GUIDELINE.md REPORT_TEMPLATE.md "$STAGING_DIR/"

# If REPORT.pdf exists, include it
[ -f REPORT.pdf ] && cp REPORT.pdf "$STAGING_DIR/" || echo "⚠️ REPORT.pdf not found yet (export from REPORT_TEMPLATE.md)"

# Strip caches
find "$STAGING_DIR" -name "__pycache__" -type d -exec rm -rf {} +  2>/dev/null || true
find "$STAGING_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$STAGING_DIR" -name ".DS_Store" -delete 2>/dev/null || true

# Build zip
zip -r "${NAME}.zip" "$STAGING_DIR" >/dev/null

# Cleanup staging
rm -rf "$STAGING_DIR"

echo "✅ Created ${NAME}.zip"
ls -lh "${NAME}.zip"
