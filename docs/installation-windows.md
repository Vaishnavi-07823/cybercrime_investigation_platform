# Windows Installation Guide

## 1. Verify Windows and virtualization

Open **Task Manager → Performance → CPU** and confirm that **Virtualization: Enabled** is shown. When it is disabled, enable Intel VT-x/VT-d or AMD-V/SVM in BIOS/UEFI.

## 2. Install or update WSL 2

Open PowerShell as Administrator:

```powershell
wsl --install
wsl --update
wsl --status
```

Restart Windows when requested.

## 3. Install Docker Desktop

During installation:

- Select the WSL 2 backend.
- Allow Docker Desktop to enable required Windows components.
- Start Docker Desktop and wait for the engine to report that it is running.

Verify in PowerShell:

```powershell
docker --version
docker compose version
docker run --rm hello-world
```

## 4. Install Git and VS Code

Verify:

```powershell
git --version
code --version
```

Recommended VS Code extensions:

- Python
- Pylance
- Docker
- ESLint
- Prettier
- REST Client
- GitLens

## 5. Check prerequisites

From the project directory, run:

```powershell
.\scripts\check-prerequisites.ps1
```

Resolve any red **MISSING - REQUIRED** entries before starting the containers.

## 6. Extract the project

Place the repository in a short path without unusual characters, for example:

```text
C:\Projects\cybercrime-investigation-platform
```

Open PowerShell in that directory.

## 7. Create the environment file

```powershell
Copy-Item .env.example .env
notepad .env
```

Change at least:

```text
APP_SECRET_KEY
ADMIN_PASSWORD
POSTGRES_PASSWORD
MINIO_SECRET_KEY
NEO4J_PASSWORD
```

Use long, unique development values. Never commit `.env`.

## 8. Start the platform

```powershell
.\scripts\bootstrap.ps1
```

Equivalent manual commands:

```powershell
docker compose pull
docker compose build
docker compose up -d
docker compose ps
```

## 9. Open the applications

- Analyst UI: `http://localhost:5173`
- FastAPI documentation: `http://localhost:8000/docs`
- MinIO console: `http://localhost:9001`
- Neo4j Browser: `http://localhost:7474`
- OpenSearch API: `http://localhost:9200`

## 10. Load the demo investigation

Run inside the backend container so no local Python installation is required:

```powershell
docker compose exec backend python /workspace/scripts/demo_seed.py
```

Refresh the analyst UI and select **Simulated BEC Investigation**.

## 11. Verify the stack

```powershell
docker compose ps
docker compose logs backend --tail 100
docker compose logs worker --tail 100
```

API health check:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

Expected result:

```text
status
------
ok
```

## Stop or reset

Stop while keeping data:

```powershell
docker compose down
```

Delete all project containers and data volumes:

```powershell
docker compose down -v --remove-orphans
```

The reset command permanently deletes the local case database, evidence objects, reports, search index and graph data.

## Common problems

### Docker engine is not running

Start Docker Desktop and wait for the engine status to become healthy.

### WSL error

```powershell
wsl --update
wsl --shutdown
```

Restart Docker Desktop afterward.

### OpenSearch exits due to memory

Increase Docker Desktop memory allocation. For this complete stack, 8 GB assigned to Docker is a reasonable development starting point.

### Port already in use

Find the process:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

Stop the conflicting application or change the left side of the relevant port mapping in `docker-compose.yml`.

### Backend starts before an infrastructure service is ready

```powershell
docker compose restart backend worker
```

### File sharing is slow

Keep the repository in the WSL Linux filesystem when performing intensive development, or use Docker Desktop's recommended WSL file-sharing configuration.
