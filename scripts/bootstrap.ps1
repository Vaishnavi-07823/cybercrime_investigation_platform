$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review the passwords before production use." -ForegroundColor Yellow
}

docker compose pull
docker compose build
docker compose up -d

docker compose ps
Write-Host "UI: http://localhost:5173" -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs" -ForegroundColor Green
