#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL="${LLM_MODEL:-llama3.1:8b}"
MODE="ollama"
OLLAMA_RUNTIME="host"

usage() {
  cat <<'EOF'
Usage: ./scripts/start.sh [option]

Options:
  --host-ollama       Use Ollama running on the host machine (default)
  --docker-ollama     Run Ollama inside the optional Compose profile
  --rules             Use the deterministic rules baseline without Ollama
  -h, --help          Show this help

Environment:
  LLM_MODEL           Ollama model to use (default: llama3.1:8b)
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

model_is_installed() {
  "$@" list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -Fxq "$MODEL"
}

wait_for_ollama() {
  local url="$1"
  local attempt
  for attempt in $(seq 1 30); do
    if curl --silent --fail "$url/api/tags" >/dev/null; then
      return 0
    fi
    sleep 1
  done
  echo "Ollama did not become ready at $url" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host-ollama)
      OLLAMA_RUNTIME="host"
      MODE="ollama"
      ;;
    --docker-ollama)
      OLLAMA_RUNTIME="docker"
      MODE="ollama"
      ;;
    --rules)
      MODE="rules"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

require_command docker
require_command curl

if [[ "$MODE" == "rules" ]]; then
  echo "Starting deterministic investigation mode."
  exec docker compose up --build
fi

if [[ "$OLLAMA_RUNTIME" == "host" ]]; then
  require_command ollama
  if ! curl --silent --fail http://localhost:11434/api/tags >/dev/null; then
    echo "Ollama is not running at http://localhost:11434." >&2
    echo "Start Ollama, then run this script again." >&2
    exit 1
  fi
  if ! model_is_installed ollama; then
    echo "Pulling local model: $MODEL"
    ollama pull "$MODEL"
  fi
  echo "Starting Compose with host Ollama and model $MODEL."
  export INVESTIGATION_MODE=ollama
  export LLM_BASE_URL="${LLM_BASE_URL:-http://host.docker.internal:11434}"
  export LLM_MODEL="$MODEL"
  exec docker compose up --build
fi

echo "Starting the Docker Ollama service."
docker compose --profile ollama up -d ollama
wait_for_ollama http://localhost:11434

if ! docker compose --profile ollama exec -T ollama ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -Fxq "$MODEL"; then
  echo "Pulling Docker model: $MODEL"
  docker compose --profile ollama exec ollama ollama pull "$MODEL"
fi

echo "Starting Compose with Docker Ollama and model $MODEL."
export INVESTIGATION_MODE=ollama
export LLM_BASE_URL=http://ollama:11434
export LLM_MODEL="$MODEL"
exec docker compose --profile ollama up --build
