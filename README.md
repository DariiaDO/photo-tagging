# Photo App

Monorepo with:

- `backend/` - Django + Django REST Framework API for upload, tagging, albums, and face grouping.
- `mobile/PhotoAlbum/` - Android client.
- `llava_service/` - local FastAPI inference service for image description.

## Target Production Topology

```text
mobile app -> nginx -> django
                   django -> llava_service
                   django -> postgres
```

`nginx` is the only external entrypoint. `llava_service` stays internal and serves `POST /analyze` for Django.

## Local Backend Development

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8080
```

By default Django uses SQLite locally. To enable Postgres, set `USE_POSTGRES=1` and the `POSTGRES_*` variables.

## Local Docker Development

Use the dev override when you want live backend code mounts and direct service ports:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Then use:

- Django API: `http://localhost:8080/api/`
- LLaVA service: `http://localhost:8001/health`

## Self-Hosted Deployment

1. Copy `.env.example` to `.env` and fill in real values.
2. Ensure Docker, Docker Compose plugin, NVIDIA drivers, and NVIDIA Container Toolkit are installed on the GPU server.
3. Start the stack:

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

4. Check services:

```bash
docker compose ps
docker compose logs -f django
docker compose logs -f llava
```

## Services

### `django`

- runs migrations on startup;
- collects static files into a shared volume;
- serves API through `gunicorn`;
- stores uploaded images in `/app/media`.

### `llava_service`

- FastAPI service with `GET /health` and `POST /analyze`;
- supports `POST /analyze/batch` for multiple multipart images;
- loads `llava-hf/llava-1.5-7b-hf` by default;
- can run in 4-bit mode with `LLAVA_LOAD_IN_4BIT=1` when CUDA is available;
- falls back to CPU when GPU is unavailable;
- accepts multipart `image` and `prompt`;
- returns JSON with `description`.

### `postgres`

- production database for Django;
- mounted on a named Docker volume.

### `nginx`

- reverse proxy for Django;
- serves `/static/` and `/media/` from Docker volumes.

## Important Environment Variables

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `USE_POSTGRES`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `LLAVA_ENDPOINT_URL`
- `LLAVA_MODEL_ID`
- `LLAVA_LOAD_IN_4BIT`
- `LLAVA_MAX_NEW_TOKENS`
- `LLAVA_TIMEOUT_SECONDS`
- `LLAVA_GENERATION_TIMEOUT_SECONDS`
- `FACE_DETECTION_ENABLED`
- `DRF_PAGE_SIZE`

## API Endpoints

- `GET /api/health/`
- `POST /api/photos/upload/`
- `GET /api/photos/?device_id=<device>&page=1`
- `GET /api/photos/?device_id=<device>&tags=Животные&category=animals&face_number=1`
- `GET /api/albums/?device_id=<device>&tags=Животные`
- `GET /api/faces/?device_id=<device>`

`POST /api/upload/` remains as a legacy alias for older clients.

## Tests

Backend tests:

```powershell
cd backend
python manage.py test photos
```

Android unit tests:

```powershell
cd mobile\PhotoAlbum
.\gradlew.bat testDebugUnitTest
```
