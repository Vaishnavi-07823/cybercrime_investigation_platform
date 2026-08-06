#!/usr/bin/env bash
set -u

required_ok=1
check_tool() {
  local name="$1"
  local command_name="$2"
  local required="$3"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf '[OK] %s\n' "$name"
  elif [[ "$required" == "required" ]]; then
    printf '[MISSING - REQUIRED] %s\n' "$name"
    required_ok=0
  else
    printf '[MISSING - OPTIONAL] %s\n' "$name"
  fi
}

printf 'Cybercrime Investigation Platform prerequisite check\n\n'
check_tool "Docker" docker required
check_tool "Git" git required
check_tool "Python" python3 optional
check_tool "Node.js" node optional
check_tool "Visual Studio Code" code optional

if command -v docker >/dev/null 2>&1; then
  docker info >/dev/null 2>&1 && echo '[OK] Docker engine is running' || {
    echo '[ERROR] Docker engine is not running'
    required_ok=0
  }
  docker compose version >/dev/null 2>&1 && echo '[OK] Docker Compose plugin' || {
    echo '[MISSING - REQUIRED] Docker Compose plugin'
    required_ok=0
  }
fi

exit $((1-required_ok))
