#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Review the passwords before production use."
fi

docker compose pull
docker compose build
docker compose up -d
docker compose ps
printf '\nUI: http://localhost:5173\nAPI docs: http://localhost:8000/docs\n'
