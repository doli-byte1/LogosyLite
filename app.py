"""FastAPI — POST /generate, GET /status/{id}, GET /output/..."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from models import load_config
from pipeline import auto_generate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="LogosyLite", version="1.0")

# Job store (in-memory)
_jobs: dict[str, dict] = {}
_MAX_JOBS = 100

config = load_config()
output_path = Path(config.output_dir)
output_path.mkdir(exist_ok=True)
app.mount("/output", StaticFiles(directory=str(output_path)), name="output")


class GenerateRequest(BaseModel):
    domain: str = Field(..., min_length=3)
    model: str | None = None
    color1: str | None = None
    color2: str | None = None
    sync: bool = False


def _trim_jobs() -> None:
    """Usun najstarsze joby jesli przekroczono limit."""
    if len(_jobs) > _MAX_JOBS:
        keys = list(_jobs.keys())
        for k in keys[: len(keys) - _MAX_JOBS]:
            del _jobs[k]


async def _run_job(job_id: str, req: GenerateRequest) -> None:
    """Background job."""
    try:
        result = await auto_generate(
            domain=req.domain,
            model_override=req.model,
            color1=req.color1,
            color2=req.color2,
        )
        _jobs[job_id] = result
    except Exception as e:
        _jobs[job_id] = {"status": "error", "error": str(e)}


@app.post("/generate")
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks) -> dict:
    """Generuj logo. sync=true czeka na wynik, false (default) uruchamia w tle."""
    if req.sync:
        try:
            result = await auto_generate(
                domain=req.domain,
                model_override=req.model,
                color1=req.color1,
                color2=req.color2,
            )
            return result
        except (ValueError, RuntimeError) as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"status": "running", "domain": req.domain}
    _trim_jobs()
    background_tasks.add_task(_run_job, job_id, req)
    return {"job_id": job_id, "status": "running"}


@app.get("/status/{job_id}")
async def status(job_id: str) -> dict:
    """Sprawdz status joba."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return _jobs[job_id]


@app.get("/jobs")
async def jobs() -> list[dict]:
    """Lista ostatnich jobow."""
    return [{"job_id": k, **v} for k, v in list(_jobs.items())[-20:]]


@app.get("/file/{domain}/{path:path}")
async def get_file(domain: str, path: str) -> FileResponse:
    """Pobierz plik z outputu."""
    file_path = (output_path / domain / path).resolve()
    # Ochrona przed path traversal
    if not str(file_path).startswith(str(output_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path))
