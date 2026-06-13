#!/usr/bin/env bash
set -euo pipefail

echo "=== UnionChatBot K8s Secrets Helper ==="
echo "Введите значения секретов (будут закодированы в base64):"
echo ""

read -rp "OPENAI_API_KEY: " OPENAI_API_KEY
read -rp "OPENAI_FOLDER_ID: " OPENAI_FOLDER_ID
read -rp "PG_PASSWORD: " PG_PASSWORD
read -rsp "LANGFUSE_SECRET_KEY: " LANGFUSE_SECRET_KEY; echo
read -rp "LANGFUSE_PUBLIC_KEY: " LANGFUSE_PUBLIC_KEY
read -rsp "REDIS_PASSWORD: " REDIS_PASSWORD; echo

echo ""
echo "=== Скопируйте эти значения в k8s/unionchatbot/02-secret.yaml ==="
echo ""

echo "  OPENAI_API_KEY: $(echo -n "$OPENAI_API_KEY" | base64)"
echo "  OPENAI_FOLDER_ID: $(echo -n "$OPENAI_FOLDER_ID" | base64)"
echo "  PG_PASSWORD: $(echo -n "$PG_PASSWORD" | base64)"
echo "  LANGFUSE_SECRET_KEY: $(echo -n "$LANGFUSE_SECRET_KEY" | base64)"
echo "  LANGFUSE_PUBLIC_KEY: $(echo -n "$LANGFUSE_PUBLIC_KEY" | base64)"
echo "  REDIS_PASSWORD: $(echo -n "$REDIS_PASSWORD" | base64)"
