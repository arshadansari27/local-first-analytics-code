# Chapter 9 Quick Start

**TL;DR:** Solve "works on my machine" with one command.

## 30-Second Start

```bash
cd code/chapter-09
make up
```

**Access:**

- Prefect UI: <http://localhost:4200>
- MinIO Console: <http://localhost:9001> (minioadmin/minioadmin)
- Evidence: <http://localhost:3000>

## 5-Minute Tour

### 1. Start Minimal Stack

```bash
make minimal
docker compose exec analytics python3 -c "import duckdb; print(duckdb.query('SELECT 42').fetchall())"
# Output: [(42,)]
```

### 2. Add MinIO Storage

```bash
make with-minio
make test-minio
# Opens MinIO console
```

### 3. Full Stack

```bash
make up
make shell
# You're now inside the container
python3 examples/duckdb_minio.py
```

## Common Commands

```bash
make up              # Start everything
make down            # Stop everything
make shell           # Enter container
make logs            # View all logs
make clean           # Nuclear option

make minimal         # Just analytics
make with-minio      # Add storage
make dev             # Dev environment
make staging         # Staging environment
```

## Dev Containers (VSCode)

1. Install "Dev Containers" extension
2. Open this folder in VSCode
3. Command Palette → "Reopen in Container"
4. Everything just works

## What You Get

### Services

- **Analytics**: Python 3.12 + DuckDB + Polars + PyArrow
- **MinIO**: S3-compatible storage (no cloud costs)
- **Prefect**: Workflow orchestration + UI
- **Evidence**: BI dashboards

### Volumes

- Your `./data` folder → mounted in container
- Your `./etl` folder → mounted in container
- MinIO data → persists in Docker volume
- Prefect state → persists in Docker volume

### Network

- Containers can talk to each other by name
- `minio:9000` works from analytics container
- `prefect:4200` works from analytics container

## Example Workflows

### Run Prefect Flow

```bash
make up
docker compose exec analytics python3 etl/flows/ingest.py
# Check UI: http://localhost:4200
```

### Query MinIO with DuckDB

```bash
make up
make test-minio  # Create bucket
docker compose exec analytics python3 examples/duckdb_minio.py
```

### Interactive Notebook

```bash
make up
docker compose exec analytics jupyter notebook --ip=0.0.0.0 --allow-root --no-browser
# Follow URL in output
```

## File Guide

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Full stack config |
| `docker-compose.minimal.yaml` | Minimal stack |
| `docker-compose.minio.yaml` | With MinIO |
| `Dockerfile` | Analytics image |
| `requirements.txt` | Python deps |
| `Makefile` | Command shortcuts |
| `.devcontainer/devcontainer.json` | VSCode config |

## Troubleshooting

### Port Already in Use

Edit `docker-compose.yaml`:

```yaml
ports:
  - "4201:4200"  # Change 4200 → 4201
```

### Permission Denied (Linux)

```bash
UID=$(id -u) GID=$(id -g) docker compose up
```

### Service Won't Start

```bash
docker compose logs -f <service-name>
```

### Rebuild After Changes

```bash
make rebuild
```

## Team Handoff

Send teammates:

```bash
git clone <repo>
cd code/chapter-09
make up
```

That's it. No installation guide. No "did you install X?". Just works.

## Multi-Environment

```bash
# Dev (verbose logs, dev data)
make dev

# Staging (staging data)
make staging
```

## Key Benefits

✅ **One command** - `make up`
✅ **Portable** - Works on Mac, Linux, Windows
✅ **Reproducible** - Pinned versions
✅ **Isolated** - No dependency conflicts
✅ **Team-ready** - Identical for everyone
✅ **Dev Containers** - IDE inside Docker

## Learn More

- Full guide: [README.md](README.md)
- File reference: [FILES.md](FILES.md)
- Interactive tour: [chapter_09_docker_compose.ipynb](chapter_09_docker_compose.ipynb)
- Detailed summary: [SUMMARY.md](SUMMARY.md)

## Need Help?

```bash
make help           # Show all commands
docker compose ps   # Show running services
docker compose logs -f  # Follow all logs
```

---

**The "Works on My Machine" problem is now solved. Forever.**
