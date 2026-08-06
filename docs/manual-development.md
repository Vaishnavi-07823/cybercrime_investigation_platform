# Running Components Outside Docker

The Docker workflow is recommended. Use this guide only for active development.

## Backend

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

You still need the infrastructure containers:

```powershell
docker compose up -d postgres redis minio opensearch neo4j
```

Create a local backend environment file or set variables so hostnames use `localhost` rather than Compose service names:

```text
DATABASE_URL=postgresql+psycopg://cybercrime:cybercrime_dev_password@localhost:5432/cybercrime
MINIO_ENDPOINT=localhost:9000
OPENSEARCH_URL=http://localhost:9200
NEO4J_URI=bolt://localhost:7687
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

Run:

```powershell
uvicorn app.main:app --reload --port 8000
```

Tests:

```powershell
pytest -q
ruff check app tests
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Production build check:

```powershell
npm run build
```

## Worker

```powershell
cd backend
celery -A app.tasks.celery_app.celery_app worker --loglevel=INFO
```

## Local LLM with Ollama

1. Install Ollama.
2. Pull a model suitable for your hardware.
3. Set:

```text
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=http://host.docker.internal:11434/v1
LLM_API_KEY=local-development-key
LLM_MODEL=<your-model-name>
```

4. Restart backend:

```powershell
docker compose restart backend
```

The deterministic narrative mode remains the safer default for initial testing.
