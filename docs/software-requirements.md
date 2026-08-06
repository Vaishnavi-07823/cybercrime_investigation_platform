# Software and Hardware Requirements

This project is designed to run through Docker Compose. You do **not** need to install PostgreSQL, Redis, MinIO, OpenSearch, Neo4j, Python packages or Node packages individually when using the containerized workflow.

## Required software for the recommended Windows setup

1. **64-bit Windows 10 or Windows 11**
2. **Hardware virtualization enabled in BIOS/UEFI**
3. **Windows Subsystem for Linux 2 (WSL 2)**
4. **Docker Desktop for Windows**
   - Includes Docker Engine, Docker CLI and Docker Compose.
5. **Git for Windows**
6. **A modern web browser**
   - Microsoft Edge, Google Chrome or Firefox.
7. **Visual Studio Code** or another source-code editor

## Optional development software

Install these only when you want to run parts of the project outside Docker:

- **Python 3.12 or 3.13**
  - Backend development, tests and the local demo-seeding script.
- **Node.js 22 or 24 LTS with npm**
  - Frontend development outside its container.
- **Postman, Bruno or Insomnia**
  - Manual API testing.
- **DBeaver or pgAdmin**
  - PostgreSQL inspection.
- **Ollama**
  - Local OpenAI-compatible LLM endpoint.
- **Windows Terminal**
  - Improved PowerShell and WSL terminal experience.

## Software supplied by Docker Compose

The project automatically creates containers for:

| Component | Purpose | Host port |
|---|---|---:|
| FastAPI backend | REST API and orchestration | 8000 |
| React/Vite frontend | Analyst interface | 5173 |
| PostgreSQL | Cases, evidence metadata and audit data | 5432 |
| Redis | Celery broker, cache and result backend | 6379 |
| MinIO | Raw-evidence and report object storage | 9000/9001 |
| OpenSearch | Event indexing and analytical search | 9200 |
| Neo4j | Entity and relationship graph | 7474/7687 |
| Celery worker | Background-task foundation | Internal |

## Recommended computer specifications

### Minimum for a small demonstration

- 4 CPU cores
- 12 GB RAM
- 25 GB free SSD space
- Stable internet connection for the first image download

### Recommended for comfortable local development

- 8 CPU cores
- 16–32 GB RAM
- 60 GB or more free SSD space
- SSD/NVMe storage

### Local LLM recommendation

A local LLM substantially increases resource requirements. The exact requirement depends on the selected model and quantization. Run the platform with `LLM_PROVIDER=none` first; enable Ollama only after the core stack is stable.

## Ports that must be available

```text
5173  Frontend
5432  PostgreSQL
6379  Redis
7474  Neo4j Browser
7687  Neo4j Bolt
8000  Backend API
9000  MinIO API
9001  MinIO Console
9200  OpenSearch
9600  OpenSearch performance analyzer
```

Change port mappings in `docker-compose.yml` when another application already occupies one of these ports.
