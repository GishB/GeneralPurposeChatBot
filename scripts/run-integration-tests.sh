#!/usr/bin/env bash
# Run integration tests against the k8s cluster via kubectl port-forward.
#
# Usage:
#   bash scripts/run-integration-tests.sh
#   bash scripts/run-integration-tests.sh -k test_postgres
#
# The script fetches YandexGPT and Langfuse credentials from the
# unionchatbot-env Secret if they are not already exported.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

NAMESPACE="unionchatbot"
DB_NAMESPACE="sevenelement-db"
LANGFUSE_NAMESPACE="langfuse"
VECTOR_NAMESPACE="sevenelement-vector"

# --------------------------------------------------------------------------- #
# Credentials
# --------------------------------------------------------------------------- #

fetch_secret() {
  local ns="$1"
  local secret="$2"
  local key="$3"
  kubectl get secret "${secret}" -n "${ns}" -o "jsonpath={.data.${key}}" | base64 -d
}

if [[ -z "${OPENAI_API_KEY:-}" || -z "${OPENAI_FOLDER_ID:-}" ]]; then
  echo "[setup] Fetching YandexGPT credentials from k8s secret ${NAMESPACE}/unionchatbot-env"
  export OPENAI_API_KEY
  export OPENAI_FOLDER_ID
  OPENAI_API_KEY="$(fetch_secret "${NAMESPACE}" "unionchatbot-env" "OPENAI_API_KEY")"
  OPENAI_FOLDER_ID="$(fetch_secret "${NAMESPACE}" "unionchatbot-env" "OPENAI_FOLDER_ID")"
fi

if [[ -z "${LANGFUSE_SECRET_KEY:-}" || -z "${LANGFUSE_PUBLIC_KEY:-}" ]]; then
  echo "[setup] Fetching Langfuse credentials from k8s secret ${NAMESPACE}/unionchatbot-env"
  export LANGFUSE_SECRET_KEY
  export LANGFUSE_PUBLIC_KEY
  LANGFUSE_SECRET_KEY="$(fetch_secret "${NAMESPACE}" "unionchatbot-env" "LANGFUSE_SECRET_KEY")"
  LANGFUSE_PUBLIC_KEY="$(fetch_secret "${NAMESPACE}" "unionchatbot-env" "LANGFUSE_PUBLIC_KEY")"
fi

# --------------------------------------------------------------------------- #
# Port-forwards
# --------------------------------------------------------------------------- #

cleanup() {
  echo "[teardown] Stopping port-forwards..."
  local pids
  pids="$(jobs -p)"
  if [[ -n "${pids}" ]]; then
    # shellcheck disable=SC2086
    kill ${pids} 2>/dev/null || true
    wait 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "[setup] Starting port-forwards..."
kubectl port-forward -n "${NAMESPACE}" svc/redis-stack 6379:6379 >/dev/null &
kubectl port-forward -n "${DB_NAMESPACE}" svc/sevenelement-db-rw 5432:5432 >/dev/null &
kubectl port-forward -n "${LANGFUSE_NAMESPACE}" svc/langfuse-web 3000:3000 >/dev/null &
kubectl port-forward -n "${VECTOR_NAMESPACE}" svc/chromadb 8000:8000 >/dev/null &
kubectl port-forward -n "${NAMESPACE}" svc/general-purpose-chatbot 8080:80 >/dev/null &

# Give kubectl a moment to print connection messages and bind ports.
sleep 2

echo "[setup] Waiting for ports..."
for port in 6379 5432 3000 8000 8080; do
  for _ in {1..60}; do
    if nc -z 127.0.0.1 "${port}" 2>/dev/null; then
      echo "[setup] 127.0.0.1:${port} is reachable"
      break 2
    fi
    sleep 1
  done
  echo "[setup] WARNING: 127.0.0.1:${port} did not become reachable in time" >&2
done

# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

echo "[setup] Running integration tests (cluster mode)..."
UNION_TEST_MODE=cluster uv run pytest tests/integration -m cluster -v "$@"
