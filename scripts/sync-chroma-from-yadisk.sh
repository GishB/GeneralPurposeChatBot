#!/usr/bin/env bash
# Sync .docx documents from Yandex.Disk into a ChromaDB collection.
#
# Requirements:
#   - rclone installed and configured (default remote: ydisk:)
#   - kubectl with access to the cluster (if CHROMA_HOST points to a k8s service)
#   - OPENAI_API_KEY and OPENAI_FOLDER_ID exported (for Yandex embeddings)
#
# Usage:
#   # 1. Port-forward ChromaDB from k8s (optional if Chroma is local):
#   kubectl port-forward -n sevenelement-vector svc/chromadb 8000:8000
#
#   # 2. Run the sync:
#   export OPENAI_API_KEY=...
#   export OPENAI_FOLDER_ID=...
#   export CHROMA_HOST=127.0.0.1
#   export CHROMA_PORT=8000
#   export COLLECTION_NAME=PRODUCTION_PROFKOM
#   bash scripts/sync-chroma-from-yadisk.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

YADISK_REMOTE="${YADISK_REMOTE:-ydisk:}"
YADISK_PATH="${YADISK_PATH:-/ППО Невинномысский Азот}"
LOCAL_DIR="${LOCAL_DIR:-$(mktemp -d -t profkom-docx-XXXX)}"
COLLECTION_NAME="${COLLECTION_NAME:-PRODUCTION_PROFKOM}"

if [[ -z "${OPENAI_API_KEY:-}" || -z "${OPENAI_FOLDER_ID:-}" ]]; then
  echo "ERROR: OPENAI_API_KEY and OPENAI_FOLDER_ID must be exported" >&2
  exit 1
fi

echo "[setup] Source: ${YADISK_REMOTE}${YADISK_PATH}"
echo "[setup] Local cache: ${LOCAL_DIR}"
echo "[setup] Target collection: ${COLLECTION_NAME}"
echo "[setup] Chroma: ${CHROMA_HOST:-127.0.0.1}:${CHROMA_PORT:-8000}"

# Download only .docx files, preserving folder structure.
echo "[sync] Downloading .docx files from Yandex.Disk..."
rclone sync \
  --include "*.docx" \
  --create-empty-src-dirs \
  "${YADISK_REMOTE}${YADISK_PATH}" \
  "${LOCAL_DIR}"

DOCX_COUNT="$(find "${LOCAL_DIR}" -type f -name '*.docx' | wc -l | tr -d ' ')"
echo "[sync] Downloaded ${DOCX_COUNT} .docx files"

if [[ "${DOCX_COUNT}" -eq 0 ]]; then
  echo "[sync] No .docx files found, nothing to index" >&2
  exit 0
fi

# Index into Chroma.
echo "[sync] Indexing documents into Chroma..."
PYTHONPATH=src uv run python -m modules.chroma_ext.scripts.db_writer "${LOCAL_DIR}"

echo "[sync] Done. Collection: ${COLLECTION_NAME}"
